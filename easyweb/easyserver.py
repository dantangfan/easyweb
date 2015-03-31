#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import types


class Header(object):
    pass


class EasyHandler(object):
    # 用于出错时候
    error_status = "500 Dude, this is whack!"
    error_headers = [('Content-Type', 'text/plain')]
    error_body = "Server Error, please debug !!!"

    # 控制变量
    status = result = None
    headers_sent = False
    headers = None
    bytes_sent = 0

    def __init__(self, stdin, stdout, stderr, environ, multithread=True, multiprocess=False):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.environ = environ
        self.multithread = multithread
        self.multiprocess = multiprocess

    def run(self, application):
        try:
            self.setup()
            self.result = application(self.environ, self.start_response)
            self.finish()
        except:
            try:
                self.handle_error()
            except:
                self.close()
                raise

    def setup(self):
        # 根据PEP333
        # 设置必要的环境变量
        env = self.environ
        env['wsgi.input'] = self.get_stdin()
        env['wsgi.errors'] = self.get_stderr()
        env['wsgi.version'] = (0, 1)
        env['wsgi.run_once'] = False
        env['wsgi.url_scheme'] = self.http_s_()
        env['wsgi.multithread'] = True
        env['wsgi.multiprocess'] = True

    def start_response(self, status, headers, exc_info=None):
        # 根据PEP333说明
        # 在提供了exc_info变量之后
        # 如果已经发送了header，就直接raise error
        # 如果没有发送header，就可以先修改status和header再发送
        # 并且要在最后将exc_info置空
        if exc_info:
            try:
                if self.headers_sent:
                    raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                exc_info = None
        elif self.headers is not None:
            raise AssertionError("headers already sent")
        self.status = status
        self.headers = Header(headers)
        return self.write

    def finish(self):
        for data in self.result:
            self.write(data)
        self.finish_content()
        self.close()

    def handle_error(self):
        if not self.headers_sent:
            self.result = self.error_output(self.environ, self.start_response)
            self.finish()

    def error_output(self, environ, start_response):
        start_response(self.error_status, self.error_headers, sys.exc_info())
        return [self.error_body]

    def finish_content(self):
        if not self.headers_sent:
            self.headers['Content-Length'] = 0
            self.send_headers()
        else:
            pass

    def send_headers(self):
        if not self.headers.haskey('Content-Length'):
            try:
                blocks = len(self.result)
            except:
                pass
            else:
                if blocks == 1:
                    self.headers['Content-Length'] = str(self.bytes_sent)
        self.headers_sent = True
        self._write('Status %s\r\n' % self.status)
        self._write(str(self.headers))

    def write(self, data):
        # 根据PEP333
        # 如果在发送数据之前
        assert type(data) is types.StringType
        if not self.status:
            raise AssertionError('write() before start_response()')
        if not self.headers_sent:
            # 根据PEP333
            # 在第一次发送数据之前，需要先把header发送出去
            # 并且一定要预先知道我们发送的数据的长度
            self.bytes_sent = len(data)
            self.send_headers()
        else:
            self.bytes_sent += len(data)
        # 这里使用一次性发送数据
        # 每次发送之后应该清空缓冲区，不要影响下次请求
        self._write(data)
        self._flush()

    def close(self):
        try:
            if hasattr(self.result, 'close'):
                self.result.close()
        finally:
            self.reset()

    def _write(self, data):
        self.stdout.write(data)

    def _flash(self):
        self.stdout.flush()

    def get_stdin(self):
        return self.stdin

    def get_stdout(self):
        return self.stdout

    def get_stderr(self):
        return self.stderr

    def reset(self):
        self.result = None
        self.headers = None
        self.status = None
        self.environ = None
        self.bytes_sent = 0
        self.headers_sent = False

    def http_s_(self):
        if self.environ.get("HTTPS") in ('yes', 'on', '1'):
            return 'https'
        return 'http'