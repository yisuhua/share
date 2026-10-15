"""Authenticated LAN file receiver; no third-party packages required."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import queue
import re
import secrets
import shutil
import socket
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .form import FileForm, FormError

LOG = logging.getLogger('share')


class UploadFailure(Exception):
    pass


def default_config() -> Path:
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.config'))
    return base / 'Share' / 'settings.json'


def valid_name(name: str) -> bool:
    """Restrict the upload to one portable Windows filename, never a path."""
    return bool(name and len(name.encode('utf-8')) <= 180
                and name not in ('.', '..') and name[-1] not in '. '
                and not re.search(r'[\x00-\x1f\x7f/\\:<>"|?*]', name)
                and name.split('.')[0].upper() not in
                {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$',
                 *(f'COM{i}' for i in '123456789¹²³'),
                 *(f'LPT{i}' for i in '123456789¹²³')})


class Settings:
    def __init__(self, config: Path | None = None, folder: Path | None = None):
        self.config = config or default_config()
        data = json.loads(self.config.read_text('utf-8')) if self.config.exists() else {}
        self.folder = Path(folder or data.get('folder', Path.home() / 'Downloads' / 'Share')).resolve()
        self.token = data.get('token') or secrets.token_urlsafe(24)
        self.max_bytes = int(data.get('max_bytes', 1024 * 1024 * 1024))
        if self.max_bytes <= 0:
            raise ValueError('max_bytes must be positive')
        self.lock = threading.RLock()
        self.events: queue.Queue = queue.Queue(maxsize=200)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._persist(self.folder)

    def _persist(self, folder: Path) -> None:
        self.config.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.settings-', dir=self.config.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump({'folder': str(folder), 'token': self.token,
                           'max_bytes': self.max_bytes}, out, ensure_ascii=False, indent=2)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, self.config)
        finally:
            Path(temp).unlink(missing_ok=True)

    def set_folder(self, folder: Path) -> None:
        target = folder.expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        # Verify write access before changing the destination.
        with tempfile.TemporaryFile(dir=target):
            pass
        with self.lock:
            self._persist(target)
            self.folder = target

    def notify(self, event: dict) -> None:
        try:
            self.events.put_nowait(event)
        except queue.Full:
            # Bound UI history; file storage and receipt are unaffected.
            try:
                self.events.get_nowait()
            except queue.Empty:
                pass
            self.events.put_nowait(event)


class ReceiverServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, address: tuple, settings: Settings):
        self.settings = settings
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = 'Share/0.1'

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, fmt, *args):
        LOG.info('%s %r', self.client_address[0], fmt % args)

    def reply(self, status: int, data: dict):
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            LOG.warning('Client disconnected before receipt was delivered')

    def authorized(self) -> bool:
        peer = ipaddress.ip_address(self.client_address[0])
        allowed = peer.is_loopback or any(peer in ipaddress.ip_network(net) for net in
                                         ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
        if not allowed or self.headers.get('Origin'):
            self.reply(403, {'error': '仅允许局域网原生客户端连接'})
            return False
        supplied = self.headers.get('Authorization', '').encode('utf-8')
        expected = ('Bearer ' + self.server.settings.token).encode('utf-8')
        if not hmac.compare_digest(supplied, expected):
            self.reply(401, {'error': '配对密码错误'})
            return False
        return True

    def do_GET(self):
        if not self.authorized():
            return
        if self.path != '/v1/info':
            self.reply(404, {'error': '接口不存在'})
            return
        self.reply(200, {'protocol': 1, 'max_bytes': self.server.settings.max_bytes,
                         'receiver': socket.gethostname(), 'form_upload': True})

    def do_POST(self):
        if not self.authorized():
            return
        url = urlsplit(self.path)
        if url.path not in ('/v1/files', '/v1/form-files'):
            self.reply(404, {'error': '接口不存在'})
            return
        names = parse_qs(url.query, keep_blank_values=True).get('name', [])
        if len(names) != 1 or not valid_name(names[0]):
            self.reply(400, {'error': '无效文件名；请使用不带路径的普通文件名'})
            return
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,12}', lengths[0]):
            self.reply(411, {'error': '必须提供唯一有效的 Content-Length，不接受 chunked'})
            return
        wire_length = int(lengths[0])
        form = None
        length = wire_length
        if url.path == '/v1/form-files':
            sizes = self.headers.get_all('X-File-Size', [])
            if len(sizes) != 1 or not re.fullmatch(r'[0-9]{1,12}', sizes[0]):
                self.reply(400, {'error': '必须提供唯一有效的 X-File-Size'})
                return
            length = int(sizes[0])
        if length > self.server.settings.max_bytes:
            self.reply(413, {'error': '文件超过大小限制'})
            return
        if url.path == '/v1/form-files':
            if not length < wire_length <= length + 8192:
                self.reply(400, {'error': 'multipart 封装长度不合理'})
                return
            try:
                form = FileForm(self.rfile, self.headers.get('Content-Type', ''), wire_length, length)
            except FormError as error:
                self.reply(400, {'error': str(error)})
                return
        digest = self.headers.get('X-Content-SHA256', '').lower()
        if not re.fullmatch('[a-f0-9]{64}', digest):
            self.reply(400, {'error': '缺少有效 SHA-256'})
            return
        with self.server.settings.lock:
            folder = self.server.settings.folder
        temp = None
        try:
            if form is not None:
                form.begin()
            if shutil.disk_usage(folder).free < length + 16 * 1024 * 1024:
                self.reply(507, {'error': '接收目录剩余空间不足'})
                return
            fd, temp = tempfile.mkstemp(prefix='.share-', suffix='.part', dir=folder)
            checksum = hashlib.sha256()
            with os.fdopen(fd, 'wb') as out:
                remaining = length
                while remaining:
                    block = self.rfile.read(min(256 * 1024, remaining))
                    if not block:
                        raise UploadFailure('上传中断；未保存文件')
                    out.write(block)
                    checksum.update(block)
                    remaining -= len(block)
                out.flush()
                os.fsync(out.fileno())
            if form is not None:
                form.finish()
            if not hmac.compare_digest(checksum.hexdigest(), digest):
                Path(temp).unlink(missing_ok=True)
                self.reply(422, {'error': '完整性校验失败；未保存文件'})
                return
            name = names[0]
            # Atomic publication without overwriting an existing destination.
            for index in range(10000):
                suffix = '' if index == 0 else f' ({index})'
                original = Path(name)
                target = folder / f'{original.stem}{suffix}{original.suffix}'
                try:
                    if os.name == 'nt':
                        os.rename(temp, target)  # Windows rename fails if target exists.
                    else:
                        os.link(temp, target)
                    break
                except FileExistsError:
                    continue
            else:
                self.reply(409, {'error': '同名文件过多'})
                return
            event = {'name': target.name, 'bytes': length, 'sha256': digest,
                     'folder': str(folder)}
            Path(temp).unlink(missing_ok=True)
            with self.server.settings.lock:
                self.server.settings.notify(event)
            LOG.info('Received %r (%d bytes)', target.name, length)
            self.reply(201, {k: event[k] for k in ('name', 'bytes', 'sha256')})
        except (UploadFailure, FormError) as exc:
            if temp is not None:
                Path(temp).unlink(missing_ok=True)
            self.reply(400, {'error': str(exc)})
        except (TimeoutError, ConnectionError):
            if temp is not None:
                Path(temp).unlink(missing_ok=True)
            self.reply(408, {'error': '连接超时或中断；请重试'})
        except OSError:
            LOG.exception('Failed to save upload')
            self.reply(507, {'error': '写入失败；请检查接收目录和磁盘空间'})
        finally:
            if temp is not None:
                Path(temp).unlink(missing_ok=True)
