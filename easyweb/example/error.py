#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('..')

from easyweb import *

@get('/404')
def e404(request):
    return notfound()
    return "This should never happen !"

@get('/403')
def e403(request):
    return forbidden()

@get('/304')
def e304(request):
    return redirect('/')
runserver()