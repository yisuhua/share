import concurrent.futures
import hashlib
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import quote

from share_receiver.core import Settings, ReceiverServer


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.settings = Settings(self.root / 'settings.json', self.root / 'received')
        self.settings.max_bytes = 1024
        self.server = ReceiverServer(('127.0.0.1', 0), self.settings)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(2)

    def request(self, name='图片.png', data=b'abc', token=None, digest=None, extra=None):
        c = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        headers = {'Authorization': 'Bearer ' + (token or self.settings.token),
                   'X-Content-SHA256': digest or hashlib.sha256(data).hexdigest()}
        headers.update(extra or {})
        c.request('POST', '/v1/files?name=' + quote(name), data, headers)
        r = c.getresponse()
        status, body = r.status, json.loads(r.read())
        c.close()
        return status, body

    def test_upload_verifies_bytes_and_publishes_receipt(self):
        status, body = self.request()
        self.assertEqual(status, 201)
        self.assertEqual((self.settings.folder / body['name']).read_bytes(), b'abc')
        self.assertEqual(body['sha256'], 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        self.assertEqual(self.settings.events.get(timeout=1)['name'], body['name'])

    def test_wrong_password_does_not_write(self):
        self.assertEqual(self.request(token='wrong')[0], 401)
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def test_digest_mismatch_does_not_leave_partial_file(self):
        self.assertEqual(self.request(digest='0' * 64)[0], 422)
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def test_over_limit_does_not_write(self):
        self.assertEqual(self.request(data=b'x' * 1025)[0], 413)
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def test_rejects_path_traversal_and_windows_device_names(self):
        for name in ('../oops', '..\\oops', 'C:abc', 'NUL.txt', 'con', '.', 'abc.', 'abc '):
            with self.subTest(name=name):
                self.assertEqual(self.request(name=name)[0], 400)
        self.assertFalse((self.root / 'oops').exists())

    def test_parallel_same_names_never_overwrite(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: self.request(name='same.txt', data=str(i).encode()), range(4)))
        self.assertTrue(all(status == 201 for status, _ in results))
        paths = list(self.settings.folder.iterdir())
        self.assertEqual(len(paths), 4)
        self.assertEqual({p.read_bytes() for p in paths}, {b'0', b'1', b'2', b'3'})

    def test_directory_change_persists_and_routes_next_upload(self):
        target = self.root / 'new folder'
        self.settings.set_folder(target)
        self.assertEqual(self.request()[0], 201)
        self.assertEqual((target / '图片.png').read_bytes(), b'abc')
        reloaded = Settings(self.root / 'settings.json')
        self.assertEqual(reloaded.folder, target)
        self.assertEqual(reloaded.token, self.settings.token)

    def test_rejects_browser_cross_origin(self):
        self.assertEqual(self.request(extra={'Origin': 'https://evil.example'})[0], 403)

    def test_truncated_upload_is_not_published(self):
        s = socket.create_connection(self.server.server_address, timeout=3)
        header = ('POST /v1/files?name=broken.bin HTTP/1.1\r\nHost: localhost\r\n'
                  f'Authorization: Bearer {self.settings.token}\r\n'
                  f'X-Content-SHA256: {hashlib.sha256(b"abc").hexdigest()}\r\n'
                  'Content-Length: 10\r\n\r\n')
        s.sendall(header.encode() + b'abc')
        s.shutdown(socket.SHUT_WR)
        self.assertIn(b' 400 ', s.recv(4096))
        s.close()
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def form_request(self, data=b'abc', trailer=None, size=None, prefix=None):
        boundary = 'native-boundary'
        start = prefix or (b'--native-boundary\r\n'
                           b'Content-Disposition: form-data; name="file"; filename="cache.tmp"\r\n'
                           b'Content-Type: application/octet-stream\r\n\r\n')
        tail = b'\r\n--native-boundary--\r\n' if trailer is None else trailer
        c = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        c.request('POST', '/v1/form-files?name=' + quote('原图.png'), start + data + tail, {
            'Authorization': 'Bearer ' + self.settings.token,
            'Content-Type': 'multipart/form-data; boundary="' + boundary + '"',
            'X-File-Size': str(len(data) if size is None else size),
            'X-Content-SHA256': hashlib.sha256(data).hexdigest()})
        response = c.getresponse()
        result = response.status, json.loads(response.read())
        c.close()
        return result

    def test_native_multipart_saves_original_bytes_and_query_filename(self):
        data = b'\x00\xff\r\n--native-boundary\r\nbytes remain file content'
        status, body = self.form_request(data)
        self.assertEqual(status, 201)
        self.assertEqual((self.settings.folder / '原图.png').read_bytes(), data)
        self.assertEqual(body['bytes'], len(data))

    def test_native_zero_byte_file(self):
        self.assertEqual(self.form_request(b'')[0], 201)
        self.assertEqual((self.settings.folder / '原图.png').read_bytes(), b'')

    def test_native_missing_closing_boundary_leaves_no_file(self):
        self.assertEqual(self.form_request(trailer=b'bad')[0], 400)
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def test_native_extra_part_is_rejected(self):
        extra = b'\r\n--native-boundary\r\nContent-Disposition: form-data; name="other"\r\n\r\nx\r\n--native-boundary--\r\n'
        self.assertEqual(self.form_request(trailer=extra)[0], 400)
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def test_native_false_file_size_is_rejected(self):
        self.assertEqual(self.form_request(size=1)[0], 400)
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def test_native_exceeds_same_file_limit_as_raw(self):
        self.assertEqual(self.form_request(b'x' * 1025)[0], 413)
        self.assertEqual(list(self.settings.folder.iterdir()), [])

    def test_native_wrong_form_field_is_rejected(self):
        prefix = b'--native-boundary\r\nContent-Disposition: form-data; name="wrong"\r\n\r\n'
        self.assertEqual(self.form_request(prefix=prefix)[0], 400)
        self.assertEqual(list(self.settings.folder.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
