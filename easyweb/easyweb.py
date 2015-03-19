#!/usr/bin/env python
# -*- coding:utf-8 -*-


import re
import Cookie
import sys
import os
import base64
import logging
import traceback
import time
import datetime


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


if type('') is not type(b''):
    def u(string):
        return string
    bytes_type = bytes
    unicode_type = str
    basestring_type = str
else:
    def u(string):
        return string.decode("unicode_escape")
    bytes_type = str
    unicode_type = unicode
    basestring_type = basestring


_UTF8_TYPES = (bytes_type, type(None))

def utf8(value):
    if isinstance(value, _UTF8_TYPES):
        return value
    else:
        return value.encode('utf-8')


_TO_UNINODE_TYPES = (unicode_type, type(None))

def to_unicode(value):
    if isinstance(value, _TO_UNINODE_TYPES):
        return value
    else:
        return value.decode("utf-8")


_unicode = to_unicode

if str is unicode_type:
    native_str = _unicode
else:
    native_str = utf8


class HTTPHeaders(dict):
    def __init__(self, *args, **kwargs):
        super(HTTPHeaders, self).__init__()
        