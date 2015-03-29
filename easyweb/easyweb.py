#!/usr/bin/env python
# -*- coding:utf-8 -*-


import re
import cgi
import Cookie
import sys
import os
import urllib
import string
import base64
import logging
import traceback
import time
import datetime
import threading
import mimetypes


ctx = threading.local()


_RESPONSE_STATUSES = {
    # Informational
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',
    # Successful
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',
    # Redirection
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',
    # Client Error
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',
    # Server Error
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended',
}

_RE_RESPONSE_STATUS = re.compile(r'^\d\d\d(\ [\w\ ]+)?$')

_RESPONSE_HEADERS = (
    'Accept-Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy-Authenticate',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Powered-By',
    'X-UA-Compatible',
)

_RESPONSE_HEADER_DICT = dict(zip(map(lambda x: x.upper(), _RESPONSE_HEADERS), _RESPONSE_HEADERS))

_HEADER_X_POWER_BY = ('X-Powered-by', 'easyweb/1.0')


class HTTPError(Exception):
    def __init__(self, code):
        super(HTTPError, self).__init__()
        self.status = "%s %s" % (code, _RE_RESPONSE_STATUS[code])

    def header(self, name, value):
        if not hasattr(self, "_headers"):
            self._headers = [_HEADER_X_POWER_BY]
        else:
            self._headers.append((name, value))

    @property
    def headers(self):
        if hasattr(self, '_headers'):
            return self._headers
        else:
            return []

    def __str__(self):
        return self.status

    __repr__ = __str__


class RedirectError(HTTPError):
    def __init__(self, code, location):
        super(RedirectError, self).__init__(code)
        self.location = location

    def __str__(self):
        return "%s %s" % (self.status, self.location)

    __repr__ = __str__


def badrequest():
    return HTTPError(400)


def unauthorized():
    return HTTPError(401)


def forbidden():
    return HTTPError(403)


def notfound():
    return HTTPError(404)


def conflict():
    return HTTPError(405)


def internalerror():
    return HTTPError(500)


def redirect(location):
    return RedirectError(301, location)


def found(location):
    return RedirectError(302, location)


def seemore(location):
    return RedirectError(303, location)


if type('') is type(b''):
    def u(string):
        return string.decode("unicode_escape")
    bytes_type = str
    unicode_type = unicode
    basestring_type = basestring
else:
    def u(string):
        return string
    bytes_type = bytes
    unicode_type = str
    basestring_type = str


_UTF8_TYPES = (bytes_type, type(None))


def _utf8(value):
    if isinstance(value, _UTF8_TYPES):
        return value
    else:
        return value.encode('utf-8')


_TO_UNINODE_TYPES = (unicode_type, type(None))


def _unicode(value):
    if isinstance(value, _TO_UNINODE_TYPES):
        return value
    else:
        return value.decode("utf-8")

_to_unicode = _unicode


def _to_str(s):
    if isinstance(s, str):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return str(s)

if str is unicode_type:
    native_str = _unicode
else:
    native_str = _utf8


def _quote(src, encoding="utf-8"):
    """
    quote src to string
    :param url:
    :return: str
    """
    if isinstance(src, unicode):
        src = src.encode(encoding)
    return urllib.quote(src)


def _unquote(src, encoding="utf-8"):
    """
    unquote str to url
    :param url:
    :param encoding:
    :return: unicode
    """
    return urllib.unquote(src).decode(encoding)


def get(path):
    """
    decorator for get method
    """
    def _decorator(func):
        func.__web_route__ = path
        func.__web_method__ = "GET"
        return func
    return _decorator


def post(path):
    """
    decorator for post method
    """
    def _decorator(func):
        func.__web_route__ = path
        func.__web_method__ = "POST"
        return func
    return _decorator


_re_route = re.compile(r'(\:[a-zA-Z_]\w*)')


def _build_regex(path):
    """
    cover path to regex to match url from request
    :param path:
    :return:
    """
    re_list = ['^']
    var_list = []
    is_var = False
    for v in _re_route.split(path):
        if is_var:
            var_name = v[1:]
            var_list.append(var_name)
            re_list.append(r'(?P<%s>[^\/]+)' % var_name)
        else:
            s = ''
            for ch in v:
                if ch in string.digits or ch in string.letters:
                    s += ch
                else:
                    s = s + '\\' + ch
            re_list.append(s)
        is_var = not is_var
    re_list.append('$')
    return ''.join(re_list)


class Route(object):
    """
    a route object is a callable object
    """
    def __init__(self, func):
        self.path = func.__web_route__
        self.method = func.__web_method__
        self.is_static = _re_route.search(self.path) is None
        if not self.is_static:
            self.route = re.compile(_build_regex(self.path))
        self.func = func

    def match(self, url):
        m = self.route.match(url)
        if m:
            return m.groups()
        return None

    def __call__(self, *args, **kwargs):
        return self.func(*args)

    def __str__(self):
        if self.is_static:
            return "Route(static,%s,path=%s)" % (self.method, self.path)
        return "Route(dynamic,%s,path=%s)" % (self.method, self.path)

    __repr__ = __str__


def _static_file_generator(fpath):
    BLOCK_SIZE = 8192
    with open(fpath, 'rb') as f:
        block = f.read(BLOCK_SIZE)
        while block:
            yield block
            block = f.read(BLOCK_SIZE)


class StaticFileRoute(object):
    def __init__(self):
        self.method = "GET"
        self.is_static = False
        self.route = re.compile("^/static/(.+)$")

    def match(self, url):
        if url.startswith('/static/'):
            return (url[1:],)
        return None

    def __call__(self, *args, **kwargs):
        fpath = os.path.join(ctx.application.document_root, args[0])
        if not os.path.isfile(fpath):
            return notfound()
        fext = os.path.splitext(fpath)[1]
        ctx.response.content_type = mimetypes.types_map.get(fext.lower(), 'application/octet-stream')
        return _static_file_generator(fpath)


def favicon_handler():
    return _static_file_generator('/favicon.ico')


class MultipartFile(object):
    def __init__(self, storage):
        self.filename = _unicode(storage.filename)
        self.file = storage.file


class Dict(dict):
    def __init__(self, names=(), values=(), **kwargs):
        super(Dict, self).__init__(**kwargs)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute %s" % key)

    def __setattr__(self, key, value):
        self[key] = value


class Request(object):

    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response

    def _parse_input(self):
        def _helper(item):
            if isinstance(item, list):
                return [_unicode(i.value) for i in item]
            if item.filename:
                return MultipartFile(item)
            return _unicode(item.value)
        fs = cgi.FieldStorage(fp=self._environ['wsgi.input'], environ=self._environ, keep_blank_values=True)
        inputs = dict()
        for key in fs:
            inputs[key] = _helper(fs[key])
        return inputs

    def _get_raw_input(self):
        if not hasattr(self, '_raw_input'):
            self._raw_input = self._parse_input()
        return self._raw_input

    def __getitem__(self, key):
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[0]
        return r

    def get(self, key, default=None):
        r = self._get_raw_input().get(key, default)
        if isinstance(r, list):
            return r[0]
        return r

    def gets(self,key):
        r = self._get_raw_input()[key]
        if isinstance(r, list):
            return r[:]
        return [r]

    def input(self, **kwargs):
        copy = Dict(**kwargs)
        raw = self._get_raw_input()
        for k, v in raw.iteritems():
            copy[k] = v[0] if isinstance(v, list) else v
        return copy

    def get_body(self):
        fp = self._environ['wsgi.input']
        return fp.read()

    @property
    def remote_addr(self):
        return self._environ.get("REMOTE_ADDR", "0.0.0.0")

    @property
    def document_root(self):
        return self._environ.get("DOCUMENT_ROOT", "")

    @property
    def query_string(self):
        return self._environ.get("QUERY_STRING", "")

    @property
    def environ(self):
        return self._environ

    @property
    def request_method(self):
        return self._environ.get("REQUEST_METHOD", "")

    @property
    def path_info(self):
        urllib.unquote(self._environ.get("PATH_INFO", ""))

    @property
    def host(self):
        return self._environ.get("HTTP_HOST", "")

    def _get_headers(self):
        if not hasattr(self, "_headers"):
            hdrs = {}
            for k, v in self._environ.iteritems():
                if k.startswith('HTTP_'):
                    hdrs[k[5:].replace('_','-').upper()] = v.decode('utf-8')
            self._headers = hdrs
        return self._headers

    @property
    def headers(self):
        return Dict(**self._get_headers())

    def header(self, header, default=None):
        return self._get_headers().get(header.upper(),default)

    def _get_cookies(self):
        if not hasattr(self, "_cookies"):
            cookies = {}
            cookie_str = self._environ.get("HTTP_COOKIE")
            if cookie_str:
                for c in cookie_str.split(';'):
                    pos = c.find('=')
                    if pos > 0:
                        cookies[c[:pos].strip()] = _unquote(c[pos+1:])
            self._cookies = cookies
        return self._cookies

    @property
    def cookies(self):
        return Dict(**self._get_cookies())

    def cookie(self, name, default=None):
        return self._get_cookies().get(name, default)





class Response(object):
    def __init__(self):
        self._status = '200 OK'
        self._headers = {"CONTENT-TYPE": 'text/html; charset=utf-8'}

    @property
    def headers(self):
        L = [(_RESPONSE_HEADER_DICT.get(k, k), v) for k, v in self._headers.iteritems()]
        if hasattr(self, '_cookies'):
            for v in self._cookies.itervalues():
                L.append(("Set-Cookie", v))
        L.append(_HEADER_X_POWER_BY)
        return L

    def header(self, name):
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        return self._headers.get(key)

    def unset_header(self, name):
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        if key in self._headers:
            del self._headers[key]

    def set_header(self, name, value):
        key = name.upper()
        if not key in _RESPONSE_HEADER_DICT:
            key = name
        self._headers[key] = _to_str(value)

    @property
    def content_type(self):
        return self.header('CONTENT-TYPE')

    @content_type.setter
    def content_type(self, value):
        if value:
            self.set_header('CONTENT-TYPE', value)
        else:
            self.unset_header('CONTENT-TYPE')

    @property
    def content_length(self):
        self.header('CONTENT-LENGTH')

    @content_length.setter
    def content_length(self, value):
        self.set_header('CONTENT-LENGTH', str(value))

    def delete_cookie(self, name):
        self.set_cookie(name , '__deleted__', expires=0)

    def set_cookie(self, name, value, max_age=None, expires=None, path="", domain=None, secure=False, http_only=True):
        if not hasattr(self, '_cookies'):
            self._cookies = {}
        L = ["%s=%s" % (_quote(name), _quote(value))]
        #if expires is not None:
        #    if isinstance(expires, (int, long, float)):
        #        L.append('Expires=%s' % datetime.datetime.fromtimestamp(expires, UTC_0).strftime('%a, %d-%b-%Y %H:%M:%S GMT'))
        if isinstance(max_age, (int, long)):
            L.append('Max-Age=%s' % max_age)
        L.append('Path=%s' % path)
        if domain:
            L.append('Domain=%s' % domain)
        if secure:
            L.append("Secure")
        if http_only:
            L.append('HttpOnly')
        self._cookies[name] = ';'.join(L)

    def unset_cookie(self, name):
        if hasattr(self, '_cookies'):
            if name in self._cookies:
                del self._cookies

    @property
    def status_code(self):
        return int(self._status[:3])

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        if isinstance(value, (int, long)):
            if 100 <= value <= 999:
                st = _RESPONSE_STATUSES.get(value, '')
                if st:
                    self._status = "%s %s" % (value, st)
                else:
                    self._status = str(value)
            else:
                raise ValueError("Bad response code: %s" % value)
        elif isinstance(value, basestring):
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if _RE_RESPONSE_STATUS.match(value):
                self._status = value
            raise ValueError("Bad response code: %s" %  value)
        else:
            raise TypeError("Bad type of response code")


def add_slash(url):
    if not url.endswith('/'):
        url += '/'
    return url

"""
class WSGIApplication(object):
    def __init__(self, document_root=None, **kwargs):
        self._running = False
        self._document_root = document_root
        self._interpreters = []

        self._get_static = {}
        self._post_static = {}
        self._get_dynamic = []
        self._post_dynamic = []

    def _check_not_running(self):
        if self._running:
            raise RuntimeError("Application is running")

    def add_url(self, func):
        self._check_not_running()
        route = Route(func)
        if route.is_static:
            if route.method == "GET":
                self._get_static[route.path] = route
            if route.method == "POST":
                self._post_static[route.path] = route
        else:
            if route.method == "GET":
                self._get_dynamic.append(route)
            if route.method == "POST":
                self._post_dynamic.append(route)
        logging.info('Add route: %s ' % str(route))



    def run(self, host='127.0.0.1', port=8888):
        from wsgiref.simple_server import make_server
        logging.info("application %s will start at %s:%s" % (self._document_root, host, port))
        server = make_server(host, port, self.get_wsgi_application(debug=True))
        server.serve_forever()
"""