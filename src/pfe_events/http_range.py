"""Bounded, seekable HTTP range reader for public archive inspection."""
import io
import urllib.request


class HTTPRangeReader(io.RawIOBase):
    def __init__(self, url, size, *, budget=64 * 1024**2, opener=urllib.request.urlopen):
        if size <= 0 or budget <= 0:
            raise ValueError('Positive archive size and transfer budget required')
        self.url, self.size, self.budget = url, size, budget
        self.opener = opener
        self.position = 0
        self.transferred = 0
        self.requests = []
        self.etag = None

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        if whence not in (0, 1, 2):
            raise ValueError('Invalid seek origin')
        position = offset + (0 if whence == 0 else self.position if whence == 1 else self.size)
        if position < 0:
            raise ValueError('Negative seek')
        self.position = position
        return position

    def read(self, size=-1):
        size = max(0, self.size-self.position) if size < 0 else min(size, max(0, self.size-self.position))
        if size == 0:
            return b''
        if size > self.budget-self.transferred:
            raise ValueError('HTTP transfer budget exceeded')
        start, end = self.position, self.position+size-1
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={start}-{end}',
                                                          'Accept-Encoding': 'identity'})
        with self.opener(request, timeout=30) as response:
            if (response.status != 206 or response.headers.get('Content-Range')
                    != f'bytes {start}-{end}/{self.size}'):
                raise ValueError('Server did not honor exact byte range')
            etag = response.headers.get('ETag')
            if self.etag is not None and etag != self.etag:
                raise ValueError('Archive changed during range reads')
            self.etag = etag
            data = response.read(size)
            self.transferred += len(data)
            if len(data) != size:
                raise ValueError('Truncated range response')
        self.requests.append({'start': start, 'end': end, 'bytes': size})
        self.position += size
        return data
