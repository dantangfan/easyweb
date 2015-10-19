#!/usr/bin/env python
# coding:utf-8

import ioloop
from ioloop import IOLoop
import collections


class StreamClosedError(Exception):
    pass


class StreamBufferFullError(Exception):
    pass


def _double_prefix(deque):
    """Get max length of tow

    :param deque:
    :return:
    """
    new_len = max(len(deque[0]) * 2,
                  (len(deque[0]) + len(deque[1])))
    _merge_prefix(deque, new_len)


def _merge_prefix(deque, size):
    if len(deque) == 1 and len(deque[0]) <= size:
        return
    prefix = []
    remaining = size
    while deque and remaining > 0:
        chunk = deque.popleft()
        if len(chunk) > remaining:
            deque.appendleft(chunk[remaining:])
            chunk = chunk[:remaining]
        prefix.append(chunk)
        remaining -= len(chunk)
    # This data structure normally just contains byte strings, but
    # the unittest gets messy if it doesn't use the default str() type,
    # so do the merge based on the type of data that's actually present.
    if prefix:
        deque.appendleft(type(prefix[0])().join(prefix))
    if not deque:
        deque.appendleft(b"")


class IOStream(object):
    def __init__(self, sock, io_loop=None, max_buffer_size=104857600, read_chunk_size=4096):
        self._sock = sock
        self._sock.setblocking(False)
        self._io_loop = io_loop or IOLoop.instance()
        self._max_buffer_size = max_buffer_size
        self._read_chunk_size = read_chunk_size
        self._read_buffer_size = 0
        self._write_buffer_size = 0
        self._read_buffer = collections.deque()
        self._write_buffer = collections.deque()
        self._closed = False
        self._connecting = False
        self._read_delimiter = None
        self._read_max_bytes = None
        self._io_loop.add_handler(sock, ioloop.POLL_IN, self._handle_event)

    def fileno(self):
        return self._sock

    def close(self):
        if not self._closed:
            self._sock.close()
        self._closed = True

    def _check_max_bytes(self, delimiter, size):
        if self._read_max_bytes is not None and size > self._read_max_bytes:
            raise IOError("Can't find %s within %s bytes" % (delimiter, size))

    def _find_read_pos(self):
        if self._read_delimiter is not None:
            if self._write_buffer:
                while True:
                    pos = self._read_buffer[0].find(self._read_delimiter)
                    if pos != -1:
                        self._check_max_bytes(self._read_delimiter, pos+len(self._read_delimiter))
                        return pos+len(self._read_delimiter)
                    if len(self._read_buffer) == 1:
                        break
                    _double_prefix(self._read_buffer)
                self._check_max_bytes(self._read_delimiter, pos+len(self._read_delimiter))
        return None

    def _try_inline_read(self):
        pos = self._find_read_pos()
        if pos is not None:
            # todo read pos has been found, read data from buffer
            pass

    def _read_bytes(self, num_bytes):
        pass

    def _read_util(self, delimiter, read_max_bytes=None):
        self._read_delimiter = delimiter
        self._read_max_bytes = read_max_bytes
        try:
            self._try_inline_read()
        except:
            raise IOError("Read util error")
        return  # in tornado, there return an future

    def _handle_event(self, sock, fd, event):
        pass

    def _handle_write(self):
        while self._write_buffer:
            try:
                num_bytes = self.write_to_fd(self._write_buffer[0])
                self._write_buffer.popleft()
                self._write_buffer_size -= num_bytes
            except:
                raise IOError("Write to fd error")
        if not self._write_buffer:
            # todo after write we may close the connection
            self.close()

    def write_to_fd(self, data):
        return self._sock.send(data)

    def write(self, data):
        assert isinstance(data, bytes)
        if self._closed:
            raise StreamClosedError
        if data:
            if self._max_buffer_size is not None and self._write_buffer_size + len(data) > self._max_buffer_size:
                raise StreamBufferFullError("Write buffer full")
            WRITE_BUFFER_CHUNK_SIZE = 128 * 1024
            for i in range(0, len(data), WRITE_BUFFER_CHUNK_SIZE):
                self._write_buffer.append(data[i:i + WRITE_BUFFER_CHUNK_SIZE])
            self._write_buffer_size += len(data)
        if not self._connecting:
            self._handle_write()
            if self._write_buffer:
                self._add_to_write_ioloop(ioloop.POLL_OUT)
        return  # in tornado, there return a future obj

    def flush(self):
        pass
