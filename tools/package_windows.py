"""Build the asset expected by the in-app updater (not a release publisher)."""
from pathlib import Path
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from share_receiver.updates import build_package
from share_receiver.version import VERSION

if __name__ == '__main__':
    target = Path(__file__).resolve().parents[1] / 'dist' / f'Share-Windows-{VERSION}.zip'
    build_package(target.parents[1], target, VERSION)
    print(target)
    root = target.parents[1]
    setup = target.with_name(f'Share-Windows-Setup-{VERSION}.zip')
    with zipfile.ZipFile(setup, 'w', zipfile.ZIP_DEFLATED) as archive:
        paths = list((root / 'share_receiver').glob('*.py'))
        paths += [root / 'install_windows.cmd', root / 'tools/install_windows.py',
                  root / 'tools/launcher.pyw', root / 'README.md']
        for path in paths: archive.write(path, path.relative_to(root).as_posix())
    print(setup)
