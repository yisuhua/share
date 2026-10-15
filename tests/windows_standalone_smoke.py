"""Build/extract/install isolated runtime; exercise live upgrade and failed-start recovery.

Only temporary directories and loopback servers are used; no Start Menu or firewall edits.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from share_receiver.core import Settings
from share_receiver.instance import acquire
from share_receiver.updates import build_package, stage_package
from tools.bundle_runtime import verify_runtime


def wait_until(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate(): return
        time.sleep(.05)
    raise AssertionError('condition timed out')


def stop_pid(pid):
    import ctypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100001, False, pid)
    if handle:
        try:
            kernel.TerminateProcess(handle, 0)
            assert kernel.WaitForSingleObject(handle, 5000) == 0
        finally: kernel.CloseHandle(handle)


def main():
    if sys.platform != 'win32': raise RuntimeError('Windows x64 only')
    output = SOURCE / 'dist'
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-build', action='store_true')
    options = parser.parse_args()
    if not options.reuse_build:
        subprocess.run([sys.executable, '-B', str(SOURCE / 'tools/package_windows.py'), '--bundle-runtime'], check=True, timeout=180)
    print('BUILD_FINISHED', flush=True)
    archive = output / 'Share-Windows-Standalone-0.1.0-x64.zip'
    print('ARTIFACT', archive, archive.stat().st_size, hashlib.sha256(archive.read_bytes()).hexdigest(), flush=True)
    with tempfile.TemporaryDirectory(prefix='Share-standalone-check-') as temp:
        base = Path(temp)
        extracted = base / '中文解压目录'
        print('EXTRACTING', flush=True)
        with zipfile.ZipFile(archive) as package: package.extractall(extracted)
        python = extracted / 'runtime/python.exe'
        installed = base / '中文安装目录/program'
        pollution = base / 'pollution'
        pollution.mkdir()
        tripwire = base / 'unexpected-site-import'
        (pollution / 'sitecustomize.py').write_text(f"from pathlib import Path\nPath({str(tripwire)!r}).write_text('bad')\n", encoding='utf-8')
        env = dict(os.environ, PATH=str(Path(os.environ['SystemRoot']) / 'System32'),
                   PYTHONHOME=str(base / 'nonexistent-python'), PYTHONPATH=str(pollution), SHARE_UPDATE_TEST='1')
        install_code = 'import sys;sys.path.insert(0,sys.argv[1]);from tools.install_windows import install;install(sys.argv[2])'
        subprocess.run([str(python), '-B', '-c', install_code, str(extracted), str(installed)], env=env, check=True, timeout=90)
        print('ISOLATED_INSTALL_FINISHED', flush=True)
        runtime = installed / 'runtime'
        python = runtime / 'python.exe'
        probe = ('import sys,ssl,hashlib,tkinter,json;root=tkinter.Tk();root.update();root.destroy();'
                 'print(json.dumps({"prefix":sys.prefix,"paths":sys.path,"tk":tkinter.TkVersion}))')
        result = subprocess.run([str(python), '-B', '-c', probe], env=env, check=True, capture_output=True, text=True, timeout=20)
        details = json.loads(result.stdout)
        assert Path(details['prefix']) == runtime
        assert all(Path(path).is_relative_to(runtime) for path in details['paths'])
        assert not tripwire.exists()
        subprocess.run([str(python), '-B', str(SOURCE / 'tests/windows_smoke.py')], env=env, check=True, timeout=30)
        subprocess.run([str(python), '-B', str(SOURCE / 'tests/curl_interop.py')], env=env, check=True, timeout=30)
        config = base / 'settings.json'
        settings = Settings(config, base / 'received')
        config_bytes = config.read_bytes()
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        ready = base / 'old-ready'
        app_env = dict(env, SHARE_INSTALL_ROOT=str(installed), SHARE_READY_FILE=str(ready))
        args = ['--headless', '--host', '127.0.0.1', '--port', str(port), '--config', str(config)]
        runner = "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('share_receiver',run_name='__main__')"
        old = subprocess.Popen([str(python), '-B', '-c', runner, str(installed / 'releases/0.1.0'), *args], env=app_env)
        live_pid = None
        gui_process = None
        def launcher_finished():
            guard = acquire(installed / 'startup.lock')
            if guard is None: return False
            guard.close()
            return True
        def transfer(name, payload):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            try:
                connection.request('POST', '/v1/files?name=' + name, payload,
                    {'Authorization': 'Bearer ' + settings.token, 'X-Content-SHA256': hashlib.sha256(payload).hexdigest()})
                response = connection.getresponse()
                receipt = json.loads(response.read())
                assert response.status == 201, receipt
                assert (settings.folder / receipt['name']).read_bytes() == payload
            finally: connection.close()
        def fixture(version, fail=False):
            source = base / version
            shutil.copytree(SOURCE / 'share_receiver', source / 'share_receiver', ignore=shutil.ignore_patterns('__pycache__'))
            module = source / 'share_receiver'
            (module / 'version.py').write_text(f'VERSION = {version!r}\n')
            if fail:
                (module / '__main__.py').write_text("raise RuntimeError('deliberate startup failure')\n")
            else:
                shutil.copy2(module / '__main__.py', module / 'real_main.py')
                (module / '__main__.py').write_text(
                    "import os\nfrom pathlib import Path\nfrom .real_main import main\n"
                    "Path(os.environ['SHARE_INSTALL_ROOT'], 'test-child-pid').write_text(str(os.getpid()))\nmain()\n")
            target = base / (version + '.zip')
            build_package(source, target, version)
            stage_package(target, installed, version)
        try:
            wait_until(ready.exists)
            transfer('before.txt', b'original')
            fixture('0.1.1')
            old.terminate()
            old.wait(5)
            # Use the real GUI restart entry, not a manually assembled launcher command.
            gui = """import sys,threading,tkinter as tk
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from share_receiver.core import Settings,ReceiverServer
from share_receiver.desktop import Desktop
from share_receiver.updates import Release
settings=Settings(Path(sys.argv[2]))
server=ReceiverServer(('127.0.0.1',int(sys.argv[3])),settings)
worker=threading.Thread(target=server.serve_forever);worker.start()
root=tk.Tk()
try:
 app=Desktop(root,settings,server);app.show_updates()
 app.update_window.release=Release('0.1.1','unused',1,'unused','')
 app.update_window.staged=True
 root.after(100,app.update_window.restart)
 root.mainloop()
finally:
 server.shutdown();server.server_close();worker.join(2)
"""
            gui_process = subprocess.Popen([str(python), '-B', '-c', gui,
                str(installed / 'releases/0.1.0'), str(config), str(port)], env=app_env)
            assert gui_process.wait(20) == 0
            pid_file = installed / 'test-child-pid'
            wait_until(pid_file.exists)
            live_pid = int(pid_file.read_text())
            def listening():
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=.3)
                try:
                    connection.request('GET', '/v1/info', headers={'Authorization': 'Bearer ' + settings.token})
                    response = connection.getresponse()
                    response.read()
                    return response.status == 200
                except OSError: return False
                finally: connection.close()
            wait_until(listening)
            transfer('after.txt', b'updated')
            assert json.loads((installed / 'current.json').read_text())['version'] == '0.1.1'
            wait_until(launcher_finished)
            print('REAL_GUI_UPGRADE_READY_AND_LAUNCHER_FINISHED', flush=True)
            stop_pid(live_pid)
            live_pid = None
            fixture('0.1.2', fail=True)
            failed = subprocess.run([str(python), '-B', str(installed / 'launcher.pyw'),
                '--target', '0.1.2', '--', *args], env=env, timeout=15)
            assert failed.returncode != 0
            live_pid = int((installed / 'test-child-pid').read_text())
            assert json.loads((installed / 'current.json').read_text())['version'] == '0.1.1'
            transfer('recovered.txt', b'recovered')
            assert config.read_bytes() == config_bytes
            verify_runtime(runtime)
            print('REAL_GUI_RESTART_RUNTIME_UNCHANGED_PASS', flush=True)
            assert not tripwire.exists()
            print('STANDALONE_RUNTIME_ISOLATION_LIVE_UPGRADE_ROLLBACK_PASS', details, flush=True)
        finally:
            if old.poll() is None:
                old.terminate()
                old.wait(5)
            if gui_process is not None and gui_process.poll() is None:
                gui_process.terminate()
                gui_process.wait(5)
            if live_pid: stop_pid(live_pid)
            # Constrain emergency cleanup to this test's private interpreter tree.
            powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            prefix = str(installed / 'runtime').replace("'", "''") + '\\'
            query = ("$prefix='" + prefix + "'; Get-CimInstance Win32_Process | "
                     "Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($prefix,[System.StringComparison]::OrdinalIgnoreCase) } | "
                     "Select-Object -ExpandProperty ProcessId")
            children = subprocess.run([str(powershell), '-NoProfile', '-Command', query],
                                      capture_output=True, text=True, timeout=10, check=True)
            for pid in children.stdout.split(): stop_pid(int(pid))
    print('WINDOWS_STANDALONE_SMOKE_PASS', flush=True)


if __name__ == '__main__': main()
