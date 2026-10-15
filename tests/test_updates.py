import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from share_receiver.updates import (UpdateError, select_release, download_release,
                                    stage_package, activate, rollback, build_package)


def release(version='0.1.1', digest='a' * 64):
    name = f'Share-Windows-{version}.zip'
    return {'tag_name': 'v' + version, 'draft': False, 'prerelease': False,
            'body': 'Release notes', 'assets': [{'name': name, 'size': 123,
            'state': 'uploaded', 'digest': 'sha256:' + digest,
            'browser_download_url': f'https://github.com/yisuhua/share/releases/download/v{version}/{name}'}]}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.install = self.base / 'program'

    def package(self, version='0.1.1', code='value = 2\n'):
        source = self.base / ('source-' + version)
        module = source / 'share_receiver'
        module.mkdir(parents=True)
        (module / '__init__.py').write_text('')
        (module / '__main__.py').write_text(code)
        target = self.base / f'{version}.zip'
        build_package(source, target, version)
        return target

    def test_release_requires_higher_stable_version_and_fixed_origin(self):
        self.assertEqual(select_release(release(), '0.1.0').version, '0.1.1')
        self.assertIsNone(select_release(release('0.1.0'), '0.1.0'))
        self.assertIsNone(select_release(release('0.0.9'), '0.1.0'))
        bad = release()
        bad['prerelease'] = True
        self.assertIsNone(select_release(bad, '0.1.0'))
        bad = release()
        bad['assets'][0]['browser_download_url'] = 'https://evil.example/update.zip'
        with self.assertRaises(UpdateError): select_release(bad, '0.1.0')
        bad = release()
        del bad['assets'][0]['digest']
        with self.assertRaises(UpdateError): select_release(bad, '0.1.0')

    def test_corrupt_download_does_not_publish_or_activate(self):
        item = select_release(release(), '0.1.0')
        target = self.base / 'update.zip'
        with self.assertRaises(UpdateError):
            download_release(item, target, opener=lambda request, **kw: io.BytesIO(b'wrong'))
        self.assertFalse(target.exists())
        self.assertFalse(self.install.exists())

    def test_verified_download_is_saved(self):
        data = b'zip bytes'
        metadata = release(digest=hashlib.sha256(data).hexdigest())
        metadata['assets'][0]['size'] = len(data)
        item = select_release(metadata, '0.1.0')
        dest = self.base / 'update.zip'
        download_release(item, dest, opener=lambda request, **kw: io.BytesIO(data))
        self.assertEqual(dest.read_bytes(), data)

    def test_stage_switch_and_rollback_preserve_settings_and_received_files(self):
        config = self.base / 'settings.json'
        config.write_text('{"folder":"original","token":"unchanged"}')
        data = self.base / 'received.png'
        data.write_bytes(b'original bytes')
        for version in ('0.1.0', '0.1.1'):
            stage_package(self.package(version), self.install, version)
            activate(self.install, version)
        self.assertEqual(json.loads((self.install / 'current.json').read_text())['version'], '0.1.1')
        self.assertEqual(rollback(self.install), '0.1.0')
        self.assertEqual(config.read_text(), '{"folder":"original","token":"unchanged"}')
        self.assertEqual(data.read_bytes(), b'original bytes')
        self.assertTrue((self.install / 'releases/0.1.1/share_receiver/__main__.py').exists())

    def test_bad_package_leaves_current_version_and_no_new_release(self):
        stage_package(self.package('0.1.0'), self.install, '0.1.0')
        activate(self.install, '0.1.0')
        bad = self.base / 'bad.zip'
        with zipfile.ZipFile(bad, 'w') as out:
            out.writestr('../escape.py', 'value=1')
            out.writestr('share-package.json', json.dumps({'schema': 1, 'version': '0.1.1', 'files': {}}))
        with self.assertRaises(UpdateError): stage_package(bad, self.install, '0.1.1')
        self.assertFalse((self.base / 'escape.py').exists())
        self.assertFalse((self.install / 'releases/0.1.1').exists())
        self.assertEqual(json.loads((self.install / 'current.json').read_text())['version'], '0.1.0')

    def test_payload_hash_mismatch_is_rejected(self):
        good = self.package()
        bad = self.base / 'tampered.zip'
        with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, 'w') as out:
            for name in src.namelist():
                out.writestr(name, b'changed' if name.endswith('__main__.py') else src.read(name))
        with self.assertRaises(UpdateError): stage_package(bad, self.install, '0.1.1')

    def test_invalid_python_is_rejected_before_activation(self):
        with self.assertRaises((UpdateError, SyntaxError)):
            stage_package(self.package(code='not valid python !'), self.install, '0.1.1')
        self.assertFalse((self.install / 'current.json').exists())

    def test_windows_case_alias_and_symlink_are_rejected(self):
        good = self.package()
        for kind in ('duplicate', 'symlink'):
            target = self.base / (kind + '.zip')
            with zipfile.ZipFile(good) as src, zipfile.ZipFile(target, 'w') as out:
                for name in src.namelist(): out.writestr(name, src.read(name))
                if kind == 'duplicate':
                    out.writestr('SHARE_RECEIVER/__main__.py', 'value=3')
                else:
                    info = zipfile.ZipInfo('share_receiver/link.py')
                    info.external_attr = (0o120777 << 16)
                    out.writestr(info, '../../outside')
            with self.assertRaises(UpdateError): stage_package(target, self.install, '0.1.1')

    def test_external_package_with_invalid_python_is_rejected_by_staging(self):
        good = self.package()
        bad = self.base / 'invalid-code.zip'
        with zipfile.ZipFile(good) as archive:
            payload = {name: archive.read(name) for name in archive.namelist()}
        payload['share_receiver/__main__.py'] = b'not valid python !'
        manifest = json.loads(payload['share-package.json'])
        manifest['files']['share_receiver/__main__.py'] = hashlib.sha256(payload['share_receiver/__main__.py']).hexdigest()
        payload['share-package.json'] = json.dumps(manifest).encode()
        with zipfile.ZipFile(bad, 'w') as archive:
            for name, data in payload.items(): archive.writestr(name, data)
        with self.assertRaises(UpdateError): stage_package(bad, self.install, '0.1.1')
        self.assertFalse((self.install / 'releases/0.1.1').exists())

    def test_cannot_activate_nonexistent_release(self):
        with self.assertRaises(UpdateError): activate(self.install, '9.9.9')
        self.assertFalse((self.install / 'current.json').exists())





class IdleGateTests(unittest.TestCase):
    def test_restart_gate_blocks_during_open_request_and_resumes(self):
        import socket
        import threading
        import time
        from share_receiver.core import Settings, ReceiverServer
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            server = ReceiverServer(('127.0.0.1', 0), Settings(base / 'settings.json', base / 'files'))
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                sock = socket.create_connection(server.server_address)
                sock.sendall(b'POST /v1/files?name=a.txt HTTP/1.1\r\n')
                deadline = time.monotonic() + 2
                while server.active == 0 and time.monotonic() < deadline: time.sleep(.01)
                self.assertGreater(server.active, 0)
                self.assertFalse(server.try_pause_idle())
                sock.close()
                deadline = time.monotonic() + 2
                while server.active and time.monotonic() < deadline: time.sleep(.01)
                self.assertTrue(server.try_pause_idle())
                with socket.create_connection(server.server_address) as rejected:
                    rejected.sendall(b'GET /v1/info HTTP/1.0\r\n\r\n')
                    try: self.assertEqual(rejected.recv(1024), b'')
                    except ConnectionResetError: pass
                server.resume()
                self.assertFalse(server.paused)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(2)


class LauncherTests(unittest.TestCase):
    setUp = UpdateTests.setUp
    package = UpdateTests.package
    def test_startup_failure_rolls_back_and_launches_previous(self):
        import shutil
        import subprocess
        import sys
        old = self.package('0.1.0', "from pathlib import Path\nPath('old-started').write_text('yes')\nimport os\nPath(os.environ['SHARE_READY_FILE']).write_text(str(os.getpid()))\n")
        new = self.package('0.1.1', "import time\ntime.sleep(5.5)\nraise RuntimeError('simulated startup failure')\n")
        stage_package(old, self.install, '0.1.0')
        stage_package(new, self.install, '0.1.1')
        activate(self.install, '0.1.0')
        shutil.copy2(Path(__file__).resolve().parents[1] / 'tools/launcher.pyw', self.install / 'launcher.pyw')
        result = subprocess.run([sys.executable, str(self.install / 'launcher.pyw'), '--target', '0.1.1'],
                                capture_output=True, timeout=15, env=dict(__import__('os').environ, SHARE_UPDATE_TEST='1'))

        self.assertEqual(json.loads((self.install / 'current.json').read_text())['version'], '0.1.0')
        import time
        deadline = time.monotonic() + 3
        marker = self.install / 'releases/0.1.0/old-started'
        while not marker.exists() and time.monotonic() < deadline: time.sleep(.05)
        self.assertTrue(marker.exists(), result.stderr)

    def test_normal_startup_with_corrupt_current_release_rolls_back(self):
        import os
        import shutil
        import subprocess
        import sys
        old = self.package('0.1.0', "from pathlib import Path\nPath('recovered').write_text('yes')\nimport os\nPath(os.environ['SHARE_READY_FILE']).write_text(str(os.getpid()))\n")
        new = self.package('0.1.1', "raise RuntimeError('broken app')\n")
        for version, package in [('0.1.0', old), ('0.1.1', new)]:
            stage_package(package, self.install, version)
            activate(self.install, version)
        shutil.copy2(Path(__file__).resolve().parents[1] / 'tools/launcher.pyw', self.install / 'launcher.pyw')
        # Corruption prevents importing application code. Stable recovery must still work.
        (self.install / 'releases/0.1.1/share_receiver/__init__.py').write_text('raise RuntimeError("broken import")')
        subprocess.run([sys.executable, str(self.install / 'launcher.pyw')], timeout=15,
                       capture_output=True, env=dict(os.environ, SHARE_UPDATE_TEST='1'))
        self.assertEqual(json.loads((self.install / 'current.json').read_text())['version'], '0.1.0')
        import time
        marker = self.install / 'releases/0.1.0/recovered'
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline: time.sleep(.05)
        self.assertTrue(marker.exists())
        # Explicit rollback also works without importing the damaged version.
        current = self.install / 'current.json'
        current.write_text(json.dumps({'version': '0.1.1', 'previous': '0.1.0'}))
        subprocess.run([sys.executable, str(self.install / 'launcher.pyw'), '--rollback'], timeout=15,
                       capture_output=True, env=dict(os.environ, SHARE_UPDATE_TEST='1'))
        self.assertEqual(json.loads(current.read_text())['version'], '0.1.0')

    def test_relative_configuration_is_resolved_before_version_cwd_changes(self):
        import os
        import shutil
        import subprocess
        import sys
        code = ("import os,sys\nfrom pathlib import Path\n"
                "Path('arguments.json').write_text(__import__('json').dumps(sys.argv[1:]))\n"
                "Path(os.environ['SHARE_READY_FILE']).write_text(str(os.getpid()))\n")
        stage_package(self.package('0.1.0', code), self.install, '0.1.0')
        activate(self.install, '0.1.0')
        shutil.copy2(Path(__file__).resolve().parents[1] / 'tools/launcher.pyw', self.install / 'launcher.pyw')
        subprocess.run([sys.executable, str(self.install / 'launcher.pyw'), '--', '--config', 'custom.json'],
                       cwd=self.base, capture_output=True, timeout=15,
                       env=dict(os.environ, SHARE_UPDATE_TEST='1'), check=True)
        args = json.loads((self.install / 'releases/0.1.0/arguments.json').read_text())
        self.assertEqual(args, ['--config', str(self.base / 'custom.json')])

    def test_repeat_launch_does_not_switch_running_version(self):
        import os
        import shutil
        import subprocess
        import sys
        from share_receiver.instance import acquire
        for version in ('0.1.0', '0.1.1'):
            stage_package(self.package(version), self.install, version)
            activate(self.install, version)
        shutil.copy2(Path(__file__).resolve().parents[1] / 'tools/launcher.pyw', self.install / 'launcher.pyw')
        guard = acquire(self.install / 'instance.lock')
        self.assertIsNotNone(guard)
        before = (self.install / 'current.json').read_bytes()
        try:
            subprocess.run([sys.executable, str(self.install / 'launcher.pyw'), '--rollback'],
                           capture_output=True, timeout=5, check=True,
                           env=dict(os.environ, SHARE_UPDATE_TEST='1'))
            self.assertEqual((self.install / 'current.json').read_bytes(), before)
        finally: guard.close()


if __name__ == '__main__': unittest.main()
