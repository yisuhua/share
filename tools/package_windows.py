"""Build first-install and update ZIP assets; never publish a release."""
import argparse
import hashlib
from pathlib import Path
import platform
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from share_receiver.updates import build_package
from share_receiver.version import VERSION
from tools.bundle_runtime import build_runtime


def setup_files(root):
    return list((root / 'share_receiver').glob('*.py')) + [
        root / 'install_windows.cmd', root / 'tools/install_windows.py',
        root / 'tools/bundle_runtime.py', root / 'tools/launcher.pyw', root / 'README.md']


def write_setup(root, target, runtime=None):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in setup_files(root): archive.write(path, path.relative_to(root).as_posix())
        if runtime:
            for path in sorted(runtime.rglob('*')):
                if path.is_file(): archive.write(path, 'runtime/' + path.relative_to(runtime).as_posix())


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle-runtime', action='store_true', help='Windows x64 only; build self-contained first-install ZIP')
    parser.add_argument('--output-dir', type=Path, default=root / 'dist')
    args = parser.parse_args()
    if args.bundle_runtime and (sys.platform != 'win32' or platform.machine().lower() != 'amd64'):
        raise SystemExit('Bundled runtime must be built and validated on Windows x64')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    update = args.output_dir / f'Share-Windows-{VERSION}.zip'
    build_package(root, update, VERSION)
    setup = args.output_dir / f'Share-Windows-Setup-{VERSION}.zip'
    write_setup(root, setup)
    outputs = [update, setup]
    if args.bundle_runtime:
        with tempfile.TemporaryDirectory(prefix='Share-runtime-build-') as temp:
            runtime = build_runtime(Path(sys.base_prefix), Path(temp) / 'runtime', platform.python_version(), 'amd64')
            standalone = args.output_dir / f'Share-Windows-Standalone-{VERSION}-x64.zip'
            write_setup(root, standalone, runtime)
            outputs.append(standalone)
    sums = args.output_dir / 'SHA256SUMS.txt'
    sums.write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n' for path in outputs), encoding='ascii')
    for path in outputs + [sums]: print(path)


if __name__ == '__main__': main()
