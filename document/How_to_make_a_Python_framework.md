自己写简单PythonWeb框架
---
##写在前面
虽然这篇文章很简单，但是依然需要一些基础知识。

- 如果你不会Python，那就不用看了
- 如果你没有使用过多个pythonWebFramework，那么强烈建议你先去使用（Tornado、Flask、Bottle、web.py）
- 如果你没有读过PEP333/PEP3333,那么你很可能不知道所以然，因此强烈建议你先去看看[PEP333](https://www.python.org/dev/peps/pep-0333/)，然后为了方便，这里还有一篇简单翻译，可以对照看[PEP333_中文](./zh_cn_PEP333.md)

好了，上面就是所有的基础知识。有了这些基础知识，就不用继续往下看了。

##框架设计
我们的目标是用python原生的包来构建一个可以响应的web框架，它非常简单：支持url路由、get、post方法，支持cookie，其他内容实现并不困难，但这里只介绍最简单的。

我们要实现的web框架最终的`helloworld`可以这样写

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from easyweb import *

@get('/')
def index(request):
    return 'hello world !'

runserver()
```

其中`@get('/')`获取了路由，并将路由注册到相应的处理函数中，`request`是浏览器发送的请求，数据由字典表示，可以在处理函数中自由调用。`return`语句将字符串响应到客户端，字符串可以是html格式的，这样就能在浏览器直接渲染成响应的网页。

上面几乎就是这篇文章要实现的所有功能。

##Request类
整个Request类最多的功能就是这只各种headers的get方法，只有一个地方需要说，就是`__init__`方法。

按照PEP333的规定，每个web框架/应用程序都必须接收两个参数`environ和start_response`，这两个参数保证了服务器能够准确的调用web应用程序（按照参数的位置调用，而不是惨素名字，者在pep333中说得很清楚）。
所以我们需要如下的初始化函数：
```python
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
```

##Response类
发送一个响应的时候，需要发送响应头和响应体。所以Response类需要提供各种header的set、unset、get方法，如：
```python
    @property
    def content_length(self):
        self.header('CONTENT-LENGTH')

    @content_length.setter
    def content_length(self, value):
        self.set_header('CONTENT-LENGTH', str(value))
```

另外，还有一个重要的方法就是
##参考文件
- [廖雪峰的官方网站](http://www.liaoxuefeng.com/wiki/001374738125095c955c1e6d8bb493182103fac9270762a000/001397616003925a3d157284cd24bc0952d6c4a7c9d8c55000)
- [pep333](./zh_cn_PEP333.md)