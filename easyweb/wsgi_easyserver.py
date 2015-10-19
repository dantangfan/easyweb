#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import types
import urllib
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
# headers直接从wsgiref拿过来的
from headers import Headers


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
        self.headers = Headers(headers)
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
        # 根据PEP333
        # 如果应用程序没有提供content-length参数
        # 我们就需要自己计算出他的长度
        # 如果返回的可迭代对象长度是1,就直接使用第一个yield的字符串的长度当成最终值
        # 或者可以在连接结束时关闭客户端
        if not self.headers.haskey('Content-Length'):
            try:
                blocks = len(self.result)
            except:
                pass
            else:
                if blocks == 1:
                    self.headers['Content-Length'] = str(self.bytes_sent)
                else:
                    pass
                    # todo
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
            # 根据PEP333
            # 如果迭代对象返回了close方法，不管这个请求如何，在请求完成时都必须调用这个方法
            if hasattr(self.result, 'close'):
                self.result.close()
        finally:
            # 每次处理完一个请求之后，需要重置各种变量
            # 因为下次的请求环境变量是不一样的
            self.reset()

    def _write(self, data):
        self.stdout.write(data)

    def _flush(self):
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


class WSGIServer(HTTPServer):
    application = None

    def server_bind(self):
        HTTPServer.server_bind(self)
        self.setup()

    def setup(self):
        env = {}

    def get_app(self):
        return self.application

    def set_app(self, app):
        self.application = app


class WSGIRequestHandler(BaseHTTPRequestHandler):
    def get_environ(self):
        # 这个函数用于初始化EasyServer的时候，需要的环境变量
        env = self.server.base_environ.copy()
        env['SERVER_PROTOCOL'] = self.request_version  # 如HTTP/1.0
        env['REQUEST_METHOD'] = self.command  # 获取GET/POST方法
        if '?' in self.path:
            path, query = self.path.split('?', 1)
        else:
            path, query = self.path, ''

        env['PATH_INFO'] = urllib.unquote(path)  # 把%、空格之类的控制字符专码，这是为安全考虑
        env['QUERY_STRING'] = query

        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host  # 这种形式：localhost
        env['REMOTE_ADDR'] = self.client_address[0]  # 这种形式：127.0.0.1

        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader

        # 这里PEP333中有说，如果请求中没有提供这个参数，就需要服务器自己处理
        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length

        for h in self.headers.headers:
            k, v = h.split(':', 1)
            k = k.replace('-', '_').upper()
            v = v.strip()
            if k in env:
                continue                    # 这里跳过content-length之类的前面已经单独处理过的
            if 'HTTP_'+k in env:
                env['HTTP_'+k] += ','+v     # 有时候有些头有多个值
            else:
                env['HTTP_'+k] = v
        return env

    def get_stderr(self):
        return sys.stderr

    def handle(self):
        # 这里的rfile是一个可读文件
        # 他在源文件中是这样定义的self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.raw_requestline = self.rfile.readline()
        # 解析self.raw_requestline的数据，如果解析出错了就直接退出
        if not self.parse_request():
            return
        handler = EasyHandler(
            self.rfile,
            self.wfile,
            self.get_stderr(),
            self.get_environ()
        )
        handler.run(self.server.get_app())


def make_server(host, port, app, server_class=WSGIServer, handle_class=WSGIRequestHandler):
    server = server_class((host, port), handle_class)
    server.set_app(app)
    return server

