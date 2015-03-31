#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('..')
try:
    from easyweb import *
except Exception, e:
    print e

@get('/')
def index(request):
    print type(request)
    return 'hello world !'


@get('/helloworld')
def helloworld(request):
    return 'hello world !'

runserver()