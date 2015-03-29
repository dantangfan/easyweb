#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
sys.path.append('..')
try:
    from easyweb import *
except Exception, e:
    print e

@get('/')
def index(request):
    return 'hello world !'


@get('/set')
def det(request):
    response = Response("check your cookie <srcipt>javascript:alert(document.cookie)</script>")
    response.set_cookie('foo','bar')
    return response

@get('/receive')
def receive(request):

    response = Response(repr(request.cookies))
    return response

runserver()