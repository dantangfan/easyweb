自己写简单PythonWeb框架
---
##写在前面
虽然这篇文章很简单，但是依然需要一些基础知识。

- 如果你不会Python，那就不用看了
- 如果你没有使用过多个pythonWebFramework，那么强烈建议你先去使用（Tornado、Flask、Bottle、web.py）
- 如果你没有读过PEP333/PEP3333,那么你很可能不知道所以然，因此强烈建议你先去看看[PEP333](https://www.python.org/dev/peps/pep-0333/)，然后为了方便，这里还有一篇简单翻译，可以对照看[PEP333_中文](./zh_cn_PEP333.md)

好了，上面就是所有的基础知识。理清这些基础知识，就不用继续往下看了，直接上代码就可以了。

**重中之重**，处略看完代码之后，可以看**[这幅图](https://www.zybuluo.com/dantangfan/note/83077)**来理清逻辑

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

##服务器

于是我们就先从服务器说起吧，如果您使用过wsgiref这个包，强烈建议您去看看他的源代码，因为我的代码多数也是从里面copy过来。

我们要写的服务器只需要满足WSGI就行，如何从网络上读取或者写入数据不是我们的目标，所以我们使用了python内置的`BaseHTTPserver`，它将负责数据的最终传输。在他的上层，我们需要实现自己的服务器处理函数，经过我们我们服务器加工过的数据必须是符合WSGI标准的。

服务器就像一个容器，他把web框架放在里面，外面连接着网络。在网络数据请求到来的时候，要先经过服务器加工处理才能到框架/应用程序手里，我们常常看到的应用都是用框架写的，有些长得如下:
```python
@get('/')
def index(request):
    return 'hello world !'
```
其实，这里的request是已经被服务器处理过的数据了，不要认为浏览器那么聪明，一下子就发过来一个你需要的数据类型。

相信你已经看过PEP333了，一个典型的WSGI应用一般长这样：

```python
def application(environ, start_response):
    """Simplest possible application object"""
    status = "200 OK"
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return ['Hello world !\n']
```

一个完整应用当然要比这个复杂点点咯

```python
def handle_request(environ, start_response):
    try:
        request = Request(environ, start_response)
    except Exception, e:
        return Response(e, "%s %s" % (500, _RESPONSE_STATUSES[500]))
    try:
        (re_url, url, callback), kwargs = find_matching_url(request)
        response = callback(request, **kwargs)
    except Exception, e:
        return handle_error(e, request)
    if not isinstance(response, Response):
        response = Response(response)
    return response.send(start_response)
```

他按照PEP333要求返回了一个可迭代对象， 但是他要返回给谁呢？当然是服务器咯。在服务器处理一次请求的时候会调用一次你的应用程序，并将你的应用程序的输出作为最终输出到web的HTTP body，服务器的run函数大致如下。

```python
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
```

那`start_response`是什么东西？这个参数是用来干什么的呢？

他是一个函数，属于服务器的函数，它主要用于处理输出和错误控制。
```python
    def start_response(self, status, headers, exc_info=None):
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
```
按照PEP333的规定，第三个参数只有出错的时候才会有值，并且每次调用之后都必须保证他这个参数的值为空，PEP333还规定，在调用这个函数之前如果已经发送了header，那么就需要抛出错误。返回的write是一个可调用的函数，这时WSGI为了和之前的框架相兼容强加的，对我们新的框架一般没神码用。

然后整个服务器框架剩余的部分几乎都是围绕者两个函数展开的，至于`handle_request`是怎么跑的就是框架的事情了，我们等等再说。

我们可以看到，服务器每处理一个请求实际上就是调用一次`run`的过程。

首先每次处理一个请求的时候都要重置环境变量`setup()`,这里加入了PEP要求的必须的环境变量，而这些环境变量只能由服务器提供，比如操作系统变量等。
```python
    def setup(self):
        env = self.environ
        env['wsgi.input'] = self.get_stdin()
        env['wsgi.errors'] = self.get_stderr()
        env['wsgi.version'] = (0, 1)
        env['wsgi.run_once'] = False
        env['wsgi.url_scheme'] = self.http_s_()
        env['wsgi.multithread'] = True
        env['wsgi.multiprocess'] = True
```

然后我们用`result`接收应用程序返回的可迭代对象。

最后`finish()`完成一次请求。
```python
    def finish(self):
        for data in self.result:
            self.write(data)
        self.finish_content()
        self.close()
```
在关闭连接之前，我们需要先把数据写回给客户端，`write()`和`finish_content()`的相互作用，保证了在第一次写回数据之前，headers已经被发送了，
```python
   def finish_content(self):
        if not self.headers_sent:
            self.headers['Content-Length'] = 0
            self.send_headers()
        else:
            pass

    def write(self, data):
        assert type(data) is types.StringType
        if not self.status:
            raise AssertionError('write() before start_response()')
        if not self.headers_sent:
            self.bytes_sent = len(data)
            self.send_headers()
        else:
            self.bytes_sent += len(data)
        self._write(data)
        self._flush()

    def send_headers(self):
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

```
在发送headers的时候，按照PEP333的要求，如果没有`Content-Length`变量，服务器会自己拟定一个变量或者直接关闭连接。

这样，我们的WSGI的服务器基本功能就差不多完成了，剩下的就是适配到`HTTPserver和BaseRequestHandler`上。这不是这篇文章要描述的，直接看代码。
```python
def make_server(host, port, app, server_class=WSGIServer, handle_class=WSGIRequestHandler):
    server = server_class((host, port), handle_class)
    server.set_app(app)
    return server
```

##框架
刚刚我们看到我们的应用程序是长这样的
```python
def handle_request(environ, start_response):
    try:
        request = Request(environ, start_response)
    except Exception, e:
        return Response(e, "%s %s" % (500, _RESPONSE_STATUSES[500]))
    try:
        (re_url, url, callback), kwargs = find_matching_url(request)
        response = callback(request, **kwargs)
    except Exception, e:
        return handle_error(e, request)
    if not isinstance(response, Response):
        response = Response(response)
    return response.send(start_response)
```

这个程序包括了我们框架所有需要的东西：一个Request，一个Response和一个错误处理。

在文章的开头，给了一个描述一次请求的流程图,[就是这幅图](https://www.zybuluo.com/dantangfan/note/83077)。在真正执行我们的应用程序的时候：
```python
@get('/')
def index(request):
    return 'hello world !'
```
这里的`request`参数其实已经是一个`Request`对象。这个对象很简单，只需要一些提取提取请求内容的功能
```python
class Request(object):

    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response

    def __getitem__(self, key):
          pass
    def get(self, key, default=None):
        pass
    def gets(self, key):
        pass
    def get_body(self):
        pass
    @property
    def remote_addr(self):
        pass
    @property
    def document_root(self):
        pass
    @property
    def query_string(self):
        pass
    @property
    def environ(self):
        pass
    @property
    def request_method(self):
        pass
    @property
    def path_info(self):
        pass
    @property
    def host(self):
        pass

    @property
    def cookies(self):
        pass
    def cookie(self, name, default=None):
        pass
```

然后我们需根据`find_matching_url(request)`url找到对应的处理函数，也就是你写的应用程序
```python
def find_matching_url(request):
    if request.request_method not in REQUEST_MAPPINGS:
        raise seemore("The HTTP request method '%s' is not supported." % request.request_method)
    for url_set in REQUEST_MAPPINGS[request.request_method]:
        match = url_set[0].search(request.path_info)
        if match is not None:
            return url_set, match.groupdict()
    raise notfound()
```

这里的`REQUEST_MAPPINGS`是我们的函数注册列表，应用启动的时候，就已经把每个函数注册到了对应的方法上。
```python
def get(url):
    """
    decorator for get method
    register
    """
    url = add_slash(url)
    def _decorator(func):
        re_url = re.compile("^%s$" % url)
        REQUEST_MAPPINGS['GET'].append((re_url, url, func))
        return func
    return _decorator
```

之后，再生成一个`Response`对象作为响应，并且调用他的`send`函数来返回数据
```python
    def send(self, start_response):
        start_response(self.status, self.headers)
        if isinstance(self._output, unicode):
            return self._output.encode("utf-8")
        return self._output
```

这个返回值就直接返回到了我们的服务器`run`函数的`result`中去了。

当然， 就如PEP333所说，框架需要实现一些服务器不提供的功能，比如`cookie`等， 框架还能自由的修改headers：
```python
class Response(object):
    def __init__(self, output="", status="200 OK"):
        """
        :param output:
        :param status:
        :return:
        """
        self._status = status
        self._headers = {'CONTENT-TYPE': 'text/html; charset=utf-8'}
        self._output = output

    @property
    def headers(self):
        pass

    def unset_header(self, name):
        pass

    def set_header(self, name, value):
        pass

    @property
    def content_type(self):
        return self.header('CONTENT-TYPE')

    def set_cookie(self, name, value, max_age=None, expires=None, path="", domain=None, secure=False, http_only=True):
        pass

    def unset_cookie(self, name):
        pass
```

然后，我们的framework就做好了！！它既包含了一个简单的框架，有包含了一个简单的服务器。

当然，需要改进的地方还有很多。但是我不打算修改了，代码和文档和翻译已经耗费了一周的时间。


##参考文件
- [廖雪峰的官方网站](http://www.liaoxuefeng.com/wiki/001374738125095c955c1e6d8bb493182103fac9270762a000/001397616003925a3d157284cd24bc0952d6c4a7c9d8c55000)
- [pep333](./zh_cn_PEP333.md)
