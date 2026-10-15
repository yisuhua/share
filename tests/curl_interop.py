"""Explicit native multipart wire-format check using real curl, not a mock."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from share_receiver.core import ReceiverServer, Settings


def main():
    curl = shutil.which('curl.exe' if sys.platform == 'win32' else 'curl')
    if curl is None:
        raise RuntimeError('curl is required for this explicit interoperability check')
    with tempfile.TemporaryDirectory(prefix='Share-curl-check-') as tmp:
        root = Path(tmp)
        settings = Settings(root / 'settings.json', root / 'received')
        server = ReceiverServer(('127.0.0.1', 0), settings)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            for index, content in enumerate((b'', bytes(range(256)) * 8192 + b'end')):
                source = root / f'payload{index}'
                source.write_bytes(content)
                name = f'原始文件{index}.bin'
                digest = hashlib.sha256(content).hexdigest()
                result = subprocess.run([
                    curl, '--silent', '--show-error', '--fail-with-body', '--noproxy', '*',
                    '--max-time', '20',
                    '-H', 'Authorization: Bearer ' + settings.token,
                    '-H', 'X-File-Size: ' + str(len(content)),
                    '-H', 'X-Content-SHA256: ' + digest,
                    '-F', 'file=@' + str(source),
                    f'http://127.0.0.1:{server.server_port}/v1/form-files?name={quote(name)}'
                ], capture_output=True, timeout=25)
                if result.returncode:
                    raise RuntimeError(result.stderr.decode(errors='replace') + result.stdout.decode(errors='replace'))
                receipt = json.loads(result.stdout)
                assert receipt['sha256'] == digest and receipt['bytes'] == len(content)
                assert (settings.folder / name).read_bytes() == content
                print('CURL_MULTIPART_PASS', len(content), 'bytes')
        finally:
            server.shutdown()
            server.server_close()
            worker.join(2)


if __name__ == '__main__':
    main()
