"""Isolated managed-install UI path. No Start Menu/user config changes."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'win32': raise RuntimeError('Windows only')
    spec = importlib.util.spec_from_file_location('installer', SOURCE / 'tools/install_windows.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    with tempfile.TemporaryDirectory(prefix='Share-managed-') as temp:
        base = Path(temp)
        install = base / '中文安装目录' / 'program'
        installer.install(install)
        # Exercise the same UTF-8 CMD template with a real Chinese-path launch.
        probe = install / '中文启动探针.pyw'
        probe.write_text("from pathlib import Path\nPath(__file__).with_suffix('.done').write_text('ok')\n", encoding='utf-8')
        shortcut = install / '中文入口.cmd'
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        shortcut.write_text(installer.shortcut_text(pythonw, probe), encoding='utf-8')
        subprocess.run(['cmd', '/c', str(shortcut)], check=True, timeout=5)
        deadline = time.monotonic() + 5
        while not probe.with_suffix('.done').exists() and time.monotonic() < deadline: time.sleep(.02)
        assert probe.with_suffix('.done').read_text() == 'ok'

        # Use exactly the staged modules, with no source-package imports retained.
        for name in list(sys.modules):
            if name == 'share_receiver' or name.startswith('share_receiver.'): del sys.modules[name]
        sys.path.insert(0, str(install / 'releases/0.1.0'))
        os.environ['SHARE_INSTALL_ROOT'] = str(install)
        from share_receiver.core import ReceiverServer, Settings
        from share_receiver.desktop import Desktop
        from share_receiver.updates import build_package, Release
        import share_receiver.update_ui as ui
        source = base / 'new-source'
        shutil.copytree(SOURCE / 'share_receiver', source / 'share_receiver')
        (source / 'share_receiver/version.py').write_text("VERSION = '0.1.1'\n")
        package = base / 'new.zip'
        build_package(source, package, '0.1.1')
        settings = Settings(base / 'custom.json', base / 'files')
        original = settings.config.read_bytes()
        server = ReceiverServer(('127.0.0.1', 0), settings)
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        root = tk.Tk()
        try:
            app = Desktop(root, settings, server)
            app.show_updates()
            update = app.update_window
            assert update.install == install.resolve()
            release = Release('0.1.1', 'unused', package.stat().st_size, 'unused', '')
            with patch.object(ui, 'check_latest', return_value=release):
                update.check_now()
                until(root, lambda: update.release is not None)
            with patch.object(ui, 'download_release', side_effect=lambda _release, target: shutil.copy2(package, target)):
                update.download()
                until(root, lambda: update.staged)
            assert json.loads((install / 'current.json').read_text())['version'] == '0.1.0'
            sock = socket.create_connection(server.server_address)
            try:
                sock.sendall(b'GET /v1/info HTTP/1.1\r\n')
                until(root, lambda: server.active > 0)
                with patch.object(ui.subprocess, 'Popen') as launch:
                    update.restart()
                    launch.assert_not_called()
            finally: sock.close()
            until(root, lambda: server.active == 0)
            with patch.object(ui.subprocess, 'Popen') as launch, patch.object(app, 'close') as close:
                update.restart()
                args = launch.call_args.args[0]
                assert args[1] == '-B'
                assert args[args.index('--config') + 1] == str(settings.config.resolve())
                assert args[args.index('--target') + 1] == '0.1.1'
                close.assert_called_once()
            assert settings.config.read_bytes() == original
        finally:
            root.destroy()
            server.shutdown()
            server.server_close()
            worker.join(2)
    print('WINDOWS_MANAGED_UPDATE_SMOKE_PASS')


def until(root, condition):
    deadline = time.monotonic() + 5
    while not condition() and time.monotonic() < deadline:
        root.update()
        time.sleep(.02)
    assert condition(), 'timed out waiting for UI/worker'


if __name__ == '__main__': main()
