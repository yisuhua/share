"""Build an app-local Windows CPython/Tk runtime, excluding user packages."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath


class BundleError(Exception):
    pass


def required_files(version):
    match = re.fullmatch(r'(3)\.(1[1-3])\.\d+', version)
    if not match:
        raise BundleError('Only CPython 3.11–3.13 releases are supported')
    tag = ''.join(match.groups())
    return {f'python{tag}.dll', 'python.exe', 'pythonw.exe', 'python3.dll',
            'vcruntime140.dll', 'LICENSE.txt', 'Lib/os.py',
            'Lib/encodings/__init__.py', 'Lib/tkinter/__init__.py',
            'DLLs/_tkinter.pyd', 'DLLs/tcl86t.dll', 'DLLs/tk86t.dll',
            'tcl/tcl8.6/init.tcl', 'tcl/tk8.6/tk.tcl', 'tcl/tk8.6/license.terms'}


def runtime_files(source, version):
    source = Path(source)
    files = []
    root_names = {'python.exe', 'pythonw.exe', 'python3.dll', 'LICENSE.txt',
                  'python' + ''.join(version.split('.')[:2]) + '.dll'}
    root_names.update(p.name for p in source.glob('vcruntime140*.dll'))
    for name in root_names:
        if (source / name).is_file(): files.append(source / name)
    excluded = {'site-packages', '__pycache__', 'test', 'tests', 'idlelib',
                'ensurepip', 'turtledemo', 'demos'}
    for directory in ('Lib', 'DLLs', 'tcl'):
        base = source / directory
        if base.is_symlink(): raise BundleError('Runtime may not contain links')
        for current, directories, names in os.walk(base, followlinks=False):
            directories[:] = [name for name in directories if name not in excluded]
            if any((Path(current) / name).is_symlink() for name in directories):
                raise BundleError('Runtime may not contain links')
            for name in names:
                path = Path(current) / name
                if name in {'sitecustomize.py', 'usercustomize.py'}: continue
                if path.is_symlink(): raise BundleError('Runtime may not contain links')
                if path.suffix.lower() not in {'.pyc', '.pyo', '.lib', '.sh'}:
                    files.append(path)
    names = {p.relative_to(source).as_posix() for p in files}
    if not required_files(version) <= names:
        raise BundleError('Runtime is missing CPython/Tk binaries, standard library or licenses')
    if any(p.is_symlink() for p in files): raise BundleError('Runtime may not contain links')
    return files


def build_runtime(source, destination, version, architecture):
    if architecture != 'amd64': raise BundleError('This package currently targets Windows x64 only')
    source, destination = Path(source), Path(destination)
    if destination.exists(): raise BundleError('Runtime destination already exists')
    files = runtime_files(source, version)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.runtime-', dir=destination.parent))
    try:
        hashes = {}
        for path in files:
            relative = path.relative_to(source).as_posix()
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            hashes[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
        tag = ''.join(version.split('.')[:2])
        pth = temp / f'python{tag}._pth'
        pth.write_text('.\nLib\nDLLs\n', encoding='ascii')
        hashes[pth.name] = hashlib.sha256(pth.read_bytes()).hexdigest()
        manifest = {'schema': 1, 'python': version, 'architecture': architecture, 'files': hashes}
        (temp / 'runtime-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        verify_runtime(temp)
        temp.rename(destination)
        return destination
    finally:
        if temp.exists(): shutil.rmtree(temp)


def verify_runtime(directory):
    directory = Path(directory)
    try:
        manifest = json.loads((directory / 'runtime-manifest.json').read_text('utf-8'))
        files = manifest['files']
        if (manifest.get('schema') != 1 or manifest.get('architecture') != 'amd64'
                or not isinstance(files, dict)
                or not required_files(manifest['python']) <= files.keys()):
            raise BundleError('Invalid runtime manifest')
        actual = set()
        for path in directory.rglob('*'):
            if path.is_symlink(): raise BundleError('Runtime may not contain links')
            if path.is_file(): actual.add(path.relative_to(directory).as_posix())
        if actual != set(files) | {'runtime-manifest.json'}:
            raise BundleError('Runtime file list changed')
        for name, digest in files.items():
            path = PurePosixPath(name)
            if (not isinstance(name, str) or '\\' in name or ':' in name
                    or path.is_absolute() or '..' in path.parts or path.as_posix() != name):
                raise BundleError('Invalid runtime path')
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
                raise BundleError('Runtime integrity check failed: ' + name)
        return manifest
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise BundleError('Cannot validate runtime: ' + str(error)) from error
