"""Stable per-user launcher. Updated application code lives in releases/."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
import re


def wait_for_exit(pid):
    if sys.platform == 'win32':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, 60000) != 0:
                    raise RuntimeError('旧程序未退出，未切换版本')
            finally: kernel.CloseHandle(handle)
    else:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try: os.kill(pid, 0)
            except ProcessLookupError: return
            time.sleep(0.1)
        raise RuntimeError('旧程序未退出，未切换版本')


def read_current(root):
    return json.loads((root / 'current.json').read_text('utf-8'))


def validate(root, version):
    if not isinstance(version, str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        raise RuntimeError('Invalid installed version')
    directory = root / 'releases' / version
    manifest = json.loads((directory / 'share-package.json').read_text('utf-8'))
    files = manifest.get('files', {})
    if (manifest.get('schema') != 1 or manifest.get('version') != version
            or not isinstance(files, dict)
            or not {'share_receiver/__init__.py', 'share_receiver/__main__.py'} <= files.keys()):
        raise RuntimeError('Invalid installed manifest')
    for name, digest in files.items():
        if not re.fullmatch(r'share_receiver/[a-z_][a-z_0-9]*\.py', name):
            raise RuntimeError('Invalid installed path')
        data = (directory / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError('Installed file corrupted: ' + name)
        compile(data, name, 'exec')


def activate(root, version):
    validate(root, version)
    current = read_current(root)
    if current.get('version') == version: return
    fd, name = tempfile.mkstemp(prefix='.current-', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump({'version': version, 'previous': current.get('version')}, out)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, root / 'current.json')
    finally: Path(name).unlink(missing_ok=True)



def acquire(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('a+b')
    stream.seek(0, 2)
    if stream.tell() == 0:
        stream.write(b'0')
        stream.flush()
    stream.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        stream.close()
        return None
    return stream

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait-pid', type=int)
    parser.add_argument('--target')
    parser.add_argument('--rollback', action='store_true')
    options, args = parser.parse_known_args()
    if args[:1] == ['--']: args = args[1:]
    # Resolve before changing the child working directory across release versions.
    for index, value in enumerate(args):
        if value == '--config' and index + 1 < len(args):
            args[index + 1] = str(Path(args[index + 1]).resolve())
        elif value.startswith('--config='):
            args[index] = '--config=' + str(Path(value.split('=', 1)[1]).resolve())
    root = Path(__file__).resolve().parent
    if options.wait_pid: wait_for_exit(options.wait_pid)
    # Serialize launchers; a running application owns instance.lock until exit.
    guard = acquire(root / 'startup.lock')
    if guard is None: return
    try:
        probe = acquire(root / 'instance.lock')
        if probe is None: return
        probe.close()
        start(root, options, args)
    finally: guard.close()


def start(root, options, args):
    current = read_current(root)
    previous = current['version'] if options.target or options.rollback else current.get('previous')
    version = current['version']
    executable = sys.executable
    if sys.platform == 'win32':
        windowless = Path(executable).with_name('pythonw.exe')
        if windowless.exists(): executable = str(windowless)
    env = dict(os.environ, SHARE_INSTALL_ROOT=str(root))
    def launch(selected):
        fd, ready_name = tempfile.mkstemp(prefix='.ready-', dir=root)
        os.close(fd)
        ready = Path(ready_name)
        ready.unlink()
        child = None
        try:
            with (root / 'startup.log').open('ab') as log:
                child = subprocess.Popen([executable, '-m', 'share_receiver', *args],
                    cwd=root / 'releases' / selected,
                    env=dict(env, SHARE_READY_FILE=str(ready)), stdout=log, stderr=log)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if ready.exists() and ready.read_text() == str(child.pid): return
                code = child.poll()
                if code is not None:
                    raise RuntimeError(f'Share 启动失败（{code}），请查看 startup.log')
                time.sleep(.05)
            raise RuntimeError('Share 启动超时，未报告就绪')
        except Exception:
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
            raise
        finally: ready.unlink(missing_ok=True)
    try:
        if options.rollback:
            activate(root, current.get('previous'))
        elif options.target:
            activate(root, options.target)
        version = read_current(root)['version']
        validate(root, version)
        launch(version)
    except Exception:
        if previous and (version != previous or options.target):
            activate(root, previous)
            launch(previous)
        raise


if __name__ == '__main__':
    try: main()
    except Exception as error:
        if sys.platform == 'win32' and os.environ.get('SHARE_UPDATE_TEST') != '1': ctypes.windll.user32.MessageBoxW(None, str(error), 'Share 更新失败', 0x10)
        else: raise
