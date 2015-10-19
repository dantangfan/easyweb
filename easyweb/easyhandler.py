#!/usr/bin/env python
# coding:utf-8
"""
HTTP connection handler for easyweb
"""

from headers import Headers
import types
import sys


class EasyHandler(object):
    def __init__(self, stream, address, request_callback):
        self._stream = stream
        self._address = address
        self._request_callback = request_callback
        self._request = None
        self._finish = False
        self._env = dict()
        # 用于出错时候
        self.error_status = "500 Dude, this is whack!"
        self.error_headers = [('Content-Type', 'text/plain')]
        self.error_body = "Server Error, please debug !!!"
        # 控制变量
        self.status = self.result = None
        self.headers_sent = False
        self.headers = None
        self.bytes_sent = 0

    def run(self, application):
        try:
            self.setup()
            self.result = application(self._env, self.start_response)
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
        self._env['wsgi.version'] = (0, 1)
        self._env['wsgi.run_once'] = False
        self._env['wsgi.url_scheme'] = self.http_s_()
        self._env['wsgi.multithread'] = False
        self._env['wsgi.multiprocess'] = False

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
            self.result = self.error_output(self._env, self.start_response)
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
            pass

    def _write(self, data):
        self._stream.write(data)

    def _flush(self):
        self._stream.flush()

    def http_s_(self):
        if self._env.get("HTTPS") in ('yes', 'on', '1'):
            return 'https'
        return 'http'

