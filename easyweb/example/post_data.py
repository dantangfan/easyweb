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
    return 'hello world !'

@get('/simple_post')
def simple(request):
    return open('html/simple_post.html', 'r').read()

@post('/test_post')
def test_post(request):

    return "foo is: %s" % request.get('foo','nothing')

runserver()