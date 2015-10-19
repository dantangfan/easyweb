#!/usr/bin/env python
# coding:utf-8

import socket
import errno
import ioloop
from iostream import IOStream
from easyhandler import EasyHandler


class HTTPServer(object):
    def __init__(self, application, io_loop=None, reuse_address=True):
        """

        :param application: is the application the return an iterable obj, there is easyweb.handler_requests
        :param io_loop:
        :param reuse_address:
        :return:
        """
        self._io_loop = io_loop if io_loop else ioloop.IOLoop.instance()
        self._application = application
        self._reuse_address = reuse_address
        self._socket = None
        self._request_queue_size = 128
        self._started = False
        self._server_address = None

    def listen(self, port=8000, address=""):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self._reuse_address:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setblocking(0)
        self._socket.bind(port, address)
        self._server_address = self._socket.getsockname()
        self._socket.listen(self._request_queue_size)

    def start(self):
        assert not self._started
        self._started = True
        self._io_loop.add_handler(self._socket, ioloop.POLL_IN, self._handle_event)
        self._io_loop.start()

    def stop(self):
        if self._started:
            self._io_loop.remove_handler(self._socket)
            self._socket.close()
        self._started = False

    def _handle_event(self, sock, fd, event):
        # there we just accept the connections
        # 128 connections at most per time
        for i in xrange(self._request_queue_size):
            try:
                conn, address = sock.accept()
            except socket.error, e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                raise
            try:
                stream = IOStream(sock=conn, io_loop=self._io_loop)
                EasyHandler(stream, address, self._application)
            except Exception, e:
                print e
