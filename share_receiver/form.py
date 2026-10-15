"""Bounded one-file multipart envelope used by the native HarmonyOS client.

The caller streams exactly X-File-Size bytes; delimiters in binary content are
never scanned or interpreted. Only the bounded envelope is parsed in memory.
"""
import re
from email import policy
from email.message import Message
from email.parser import BytesHeaderParser


class FormError(ValueError):
    pass


class FileForm:
    def __init__(self, stream, content_type: str, wire_size: int, file_size: int):
        self.stream = stream
        self.wire_size = wire_size
        self.file_size = file_size
        self.consumed = 0
        header = Message()
        header['Content-Type'] = content_type
        boundary = header.get_param('boundary')
        if (header.get_content_type() != 'multipart/form-data' or not isinstance(boundary, str)
                or not re.fullmatch(r"[0-9A-Za-z'()+_,./:=?-]{1,70}", boundary)):
            raise FormError('无效 multipart 边界')
        self.boundary = boundary.encode('ascii')

    def _line(self) -> bytes:
        remaining = min(4096 - self.consumed, self.wire_size - self.consumed)
        if remaining <= 0:
            raise FormError('multipart 头部过长或不完整')
        line = self.stream.readline(remaining + 1)
        self.consumed += len(line)
        if len(line) > remaining or not line.endswith(b'\r\n'):
            raise FormError('multipart 头部过长或不完整')
        return line

    def begin(self):
        if self._line() != b'--' + self.boundary + b'\r\n':
            raise FormError('multipart 起始边界不匹配')
        lines = []
        while True:
            line = self._line()
            if line == b'\r\n':
                break
            lines.append(line)
        headers = BytesHeaderParser(policy=policy.default).parsebytes(b''.join(lines) + b'\r\n')
        if (headers.defects or len(headers.get_all('Content-Disposition', [])) != 1
                or headers.get_content_disposition() != 'form-data'
                or headers.get_param('name', header='Content-Disposition') != 'file'
                or headers.get('Content-Transfer-Encoding')):
            raise FormError('仅支持一个名为 file 的原始文件字段')
        tail_size = self.wire_size - self.consumed - self.file_size
        expected = b'\r\n--' + self.boundary + b'--'
        if tail_size not in (len(expected), len(expected) + 2):
            raise FormError('文件大小与 multipart 封装长度不匹配')

    def finish(self):
        tail_size = self.wire_size - self.consumed - self.file_size
        tail = self.stream.read(tail_size)
        expected = b'\r\n--' + self.boundary + b'--'
        if tail not in (expected, expected + b'\r\n'):
            raise FormError('multipart 结束边界不匹配')
