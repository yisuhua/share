"""One-time per-user installation; subsequent updates are handled inside Share."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from share_receiver.updates import build_package, stage_package, activate, read_current
from share_receiver.version import VERSION


def install(root):
    root = Path(root)
    if read_current(root):
        raise RuntimeError('Share 已安装，请从应用内检查更新；本安装程序不会覆盖现有安装。')
    with tempfile.TemporaryDirectory() as temp:
        package = Path(temp) / 'install.zip'
        build_package(SOURCE, package, VERSION)
        stage_package(package, root, VERSION)
    shutil.copy2(SOURCE / 'tools/launcher.pyw', root / 'launcher.pyw')
    activate(root, VERSION)
    return root / 'launcher.pyw'


def shortcut_text(executable, launcher):
    return f'@chcp 65001 >nul\n@echo off\nstart "" "{executable}" "{launcher}"\n'


if __name__ == '__main__':
    if sys.platform != 'win32': raise SystemExit('此安装入口仅用于 Windows')
    root = Path(os.environ['LOCALAPPDATA']) / 'Share' / 'program'
    launcher = install(root)
    desktop = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs'
    desktop.mkdir(parents=True, exist_ok=True)
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    shortcut = desktop / 'Share.cmd'
    shortcut.write_text(shortcut_text(pythonw, launcher), encoding='utf-8')
    subprocess.Popen([str(pythonw), str(launcher)])
    print('安装完成。后续在 Share 内检查更新。')
