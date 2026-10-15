"""First-install runtime isolation and integrity, without pretending to run Windows."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.bundle_runtime import build_runtime, verify_runtime, BundleError


class RuntimeBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'python'
        for name in ['python.exe', 'pythonw.exe', 'python3.dll', 'python313.dll',
                     'vcruntime140.dll', 'LICENSE.txt', 'Lib/os.py',
                     'Lib/encodings/__init__.py', 'Lib/tkinter/__init__.py',
                     'DLLs/_tkinter.pyd', 'DLLs/tcl86t.dll', 'DLLs/tk86t.dll',
                     'tcl/tcl8.6/init.tcl', 'tcl/tk8.6/tk.tcl', 'tcl/tk8.6/license.terms']:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture')
        self.destination = self.base / 'runtime'

    def build(self):
        return build_runtime(self.source, self.destination, '3.13.14', 'amd64')

    def test_runtime_omits_user_packages_and_uses_isolated_search_paths(self):
        for name in ['Lib/site-packages/private.py', 'Lib/__pycache__/os.pyc',
                     'Lib/test/test_os.py', 'secret.txt']:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('do not distribute')
        self.build()
        self.assertFalse((self.destination / 'Lib/site-packages').exists())
        self.assertFalse((self.destination / 'Lib/test').exists())
        self.assertFalse((self.destination / 'secret.txt').exists())
        self.assertEqual((self.destination / 'python313._pth').read_text().splitlines(), ['.', 'Lib', 'DLLs'])
        manifest = verify_runtime(self.destination)
        self.assertEqual(manifest['python'], '3.13.14')
        self.assertEqual(manifest['architecture'], 'amd64')
        self.assertIn('LICENSE.txt', manifest['files'])
        self.assertIn('tcl/tk8.6/license.terms', manifest['files'])

    def test_missing_tk_or_license_never_publishes_runtime(self):
        (self.source / 'DLLs/_tkinter.pyd').unlink()
        with self.assertRaises(BundleError): self.build()
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.base.glob('.runtime-*')), [])

    def test_modified_and_extra_runtime_files_fail_integrity(self):
        self.build()
        path = self.destination / 'python.exe'
        data = path.read_bytes()
        path.write_bytes(b'corrupted')
        with self.assertRaises(BundleError): verify_runtime(self.destination)
        path.write_bytes(data)
        (self.destination / 'extra.py').write_text('unexpected')
        with self.assertRaises(BundleError): verify_runtime(self.destination)

    def test_manifest_path_traversal_is_rejected(self):
        self.build()
        path = self.destination / 'runtime-manifest.json'
        data = json.loads(path.read_text())
        data['files']['../outside'] = '0' * 64
        path.write_text(json.dumps(data))
        with self.assertRaises(BundleError): verify_runtime(self.destination)

    def test_first_install_copies_bundled_runtime_and_keeps_source(self):
        import shutil
        from tools.install_windows import install
        source = self.base / 'setup'
        shutil.copytree(Path(__file__).resolve().parents[1] / 'share_receiver', source / 'share_receiver',
                        ignore=shutil.ignore_patterns('__pycache__'))
        (source / 'tools').mkdir()
        shutil.copy2(Path(__file__).resolve().parents[1] / 'tools/launcher.pyw', source / 'tools/launcher.pyw')
        build_runtime(self.source, source / 'runtime', '3.13.14', 'amd64')
        destination = self.base / 'installed'
        launcher = install(destination, source=source)
        self.assertEqual(launcher, destination / 'launcher.pyw')
        self.assertTrue((destination / 'runtime/pythonw.exe').exists())
        verify_runtime(destination / 'runtime')
        self.assertTrue((source / 'runtime/pythonw.exe').exists())
        self.assertEqual(json.loads((destination / 'current.json').read_text())['version'], '0.1.0')
        before = (destination / 'current.json').read_bytes()
        with self.assertRaises(Exception): install(destination, source=source)
        self.assertEqual((destination / 'current.json').read_bytes(), before)

    def test_corrupt_bundled_runtime_leaves_install_destination_absent(self):
        import shutil
        from tools.install_windows import install
        source = self.base / 'setup'
        shutil.copytree(Path(__file__).resolve().parents[1] / 'share_receiver', source / 'share_receiver',
                        ignore=shutil.ignore_patterns('__pycache__'))
        (source / 'tools').mkdir()
        shutil.copy2(Path(__file__).resolve().parents[1] / 'tools/launcher.pyw', source / 'tools/launcher.pyw')
        build_runtime(self.source, source / 'runtime', '3.13.14', 'amd64')
        (source / 'runtime/python.exe').write_text('corrupt')
        destination = self.base / 'installed'
        with self.assertRaises(BundleError): install(destination, source=source)
        self.assertFalse(destination.exists())

    def test_actual_update_restart_disables_runtime_bytecode_writes(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        from share_receiver.update_ui import UpdateWindow
        update = object.__new__(UpdateWindow)
        update.install = self.base / 'program'
        update.release = SimpleNamespace(version='0.1.1')
        update.status = SimpleNamespace(set=Mock())
        update.desktop = SimpleNamespace(
            server=SimpleNamespace(try_pause_idle=lambda: True, server_address=('127.0.0.1', 8765), server_port=8765),
            settings=SimpleNamespace(config=self.base / 'settings.json'), close=Mock())
        with patch('share_receiver.update_ui.subprocess.Popen') as launch:
            update.restart()
            self.assertEqual(launch.call_args.args[0][1], '-B')


if __name__ == '__main__': unittest.main()
