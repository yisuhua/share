"""Verified, versioned updates. User settings and received files live elsewhere."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit

MAX_PACKAGE = 32 * 1024 * 1024
API = 'https://api.github.com/repos/yisuhua/share/releases/latest'


class UpdateError(Exception):
    pass


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        raise UpdateError('版本号无效')
    return tuple(map(int, value.split('.')))


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    size: int
    sha256: str
    notes: str


class GithubRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname not in {
                'github.com', 'api.github.com', 'release-assets.githubusercontent.com',
                'objects.githubusercontent.com'}:
            raise UpdateError('更新下载重定向到非 GitHub 地址')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(request, **kwargs):
    return build_opener(GithubRedirect()).open(request, **kwargs)


def select_release(payload, current_version):
    if payload.get('draft') or payload.get('prerelease'):
        return None
    version = str(payload.get('tag_name', '')).removeprefix('v')
    if version_tuple(version) <= version_tuple(current_version):
        return None
    name = f'Share-Windows-{version}.zip'
    assets = [a for a in payload.get('assets', []) if a.get('name') == name]
    if len(assets) != 1:
        raise UpdateError('发布版本缺少唯一的 Windows 更新包')
    asset = assets[0]
    url = f'https://github.com/yisuhua/share/releases/download/v{version}/{name}'
    digest = asset.get('digest', '')
    size = asset.get('size')
    if (asset.get('browser_download_url') != url or asset.get('state') != 'uploaded'
            or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest)
            or type(size) is not int or not 0 < size <= MAX_PACKAGE):
        raise UpdateError('更新包地址、大小或 SHA-256 校验信息无效')
    return Release(version, url, size, digest[7:], str(payload.get('body', ''))[:8000])


def check_latest(current_version, opener=open_url):
    try:
        with opener(Request(API, headers={'User-Agent': 'Share-Updater', 'Accept': 'application/vnd.github+json'}), timeout=30) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise UpdateError('更新信息过大')
        return select_release(json.loads(raw), current_version)
    except HTTPError as error:
        if error.code == 404:
            raise UpdateError('尚未发布可用的正式更新版本') from error
        raise


def download_release(release, target, opener=open_url):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=target.parent, prefix='.download-')
    try:
        digest, count = hashlib.sha256(), 0
        with os.fdopen(fd, 'wb') as out, opener(Request(release.url, headers={'User-Agent': 'Share-Updater'}), timeout=30) as response:
            while block := response.read(256 * 1024):
                count += len(block)
                if count > release.size or count > MAX_PACKAGE:
                    raise UpdateError('下载大小与发布信息不符')
                out.write(block)
                digest.update(block)
            if count != release.size or digest.hexdigest() != release.sha256:
                raise UpdateError('更新包校验失败，已保留当前版本')
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def build_package(source, target, version):
    version_tuple(version)
    files = {}
    content = {}
    for path in sorted((Path(source) / 'share_receiver').glob('*.py')):
        name = 'share_receiver/' + path.name
        data = path.read_bytes()
        compile(data, name, 'exec')
        files[name] = hashlib.sha256(data).hexdigest()
        content[name] = data
    if not {'share_receiver/__init__.py', 'share_receiver/__main__.py'} <= files.keys():
        raise UpdateError('程序入口缺失')
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in content.items(): archive.writestr(name, data)
        archive.writestr('share-package.json', json.dumps({'schema': 1, 'version': version, 'files': files}))


def stage_package(package, root, expected_version):
    version_tuple(expected_version)
    root = Path(root)
    releases = root / 'releases'
    releases.mkdir(parents=True, exist_ok=True)
    destination = releases / expected_version
    if destination.exists():
        raise UpdateError('该版本已暂存，请先重启或使用其他版本号')
    temp = Path(tempfile.mkdtemp(prefix='.stage-', dir=root))
    try:
        with zipfile.ZipFile(package) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) > 100 or len({n.casefold() for n in names}) != len(names):
                raise UpdateError('更新包包含重复文件')
            if sum(e.file_size for e in entries) > MAX_PACKAGE:
                raise UpdateError('更新包解压后过大')
            for entry in entries:
                if (entry.filename != 'share-package.json' and not re.fullmatch(r'share_receiver/[a-z_][a-z_0-9]*\.py', entry.filename)) or stat.S_ISLNK(entry.external_attr >> 16):
                    raise UpdateError('更新包包含非法路径或链接')
            if 'share-package.json' not in names:
                raise UpdateError('更新清单缺失')
            manifest = json.loads(archive.read('share-package.json'))
            files = manifest.get('files', {})
            if (manifest.get('schema') != 1 or manifest.get('version') != expected_version
                    or not isinstance(files, dict)
                    or set(names) != set(files) | {'share-package.json'}
                    or not {'share_receiver/__init__.py', 'share_receiver/__main__.py'} <= files.keys()):
                raise UpdateError('更新清单无效')
            for name, digest in files.items():
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != digest:
                    raise UpdateError('更新文件校验失败')
                compile(data, name, 'exec')
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (temp / 'share-package.json').write_text(json.dumps(manifest), encoding='utf-8')
        temp.rename(destination)
        return destination
    except (ValueError, KeyError, TypeError, zipfile.BadZipFile, SyntaxError) as error:
        raise UpdateError('更新包无效：' + str(error)) from error
    finally:
        if temp.exists(): shutil.rmtree(temp)


def read_current(root):
    path = Path(root) / 'current.json'
    return json.loads(path.read_text('utf-8')) if path.exists() else {}


def validate_installed(root, version):
    version_tuple(version)
    directory = Path(root) / 'releases' / version
    path = directory / 'share-package.json'
    if not path.is_file(): raise UpdateError('目标版本未安装')
    manifest = json.loads(path.read_text('utf-8'))
    files = manifest.get('files', {})
    if (manifest.get('schema') != 1 or manifest.get('version') != version
            or not isinstance(files, dict)
            or not {'share_receiver/__init__.py', 'share_receiver/__main__.py'} <= files.keys()):
        raise UpdateError('已安装版本清单无效')
    for name, digest in files.items():
        if not re.fullmatch(r'share_receiver/[a-z_][a-z_0-9]*\.py', name):
            raise UpdateError('已安装版本路径无效')
        data = (directory / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise UpdateError('已暂存文件损坏，请保留旧版本并联系维护者')
        compile(data, name, 'exec')
    return directory


def activate(root, version):
    version_tuple(version)
    root = Path(root)
    validate_installed(root, version)
    current = read_current(root)
    if current.get('version') == version: return
    fd, name = tempfile.mkstemp(prefix='.current-', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump({'version': version, 'previous': current.get('version')}, out)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, root / 'current.json')
    finally:
        Path(name).unlink(missing_ok=True)


def rollback(root):
    previous = read_current(root).get('previous')
    if not previous: raise UpdateError('没有可回退的旧版本')
    activate(root, previous)
    return previous
