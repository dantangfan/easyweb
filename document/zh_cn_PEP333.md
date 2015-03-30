##摘要
本文档的主要目的是拟定web服务器和Python与web应用程序或框架之间的标准接口，来加强web应用程序在不同web服务器之间的可移植性。

##基本原理和目标
python目前拥有大量的web框架 ，如 Zope, Quixote, Webware, SkunkWeb, PSO, and Twisted Web等。过多的选择对新手来说往往是个问题，因为总的来说，web框架的选择直接限制了web服务器的选择，反之亦然。

相比之下，虽然java也有很多web框架，但是java的`servlet`API能够让用任意java-web框架写出来的应用程序运行在支持`servlet`API的web服务器上。

在服务器对这种Python API（不管这些服务器使用Python写的还是内嵌Python或是通过网关协议如CGI来启动Python）的使用和普及，将把人们对web框架和web服务器的选择分离开，让用户自由的选择自己喜欢的组合，同时让框架和服务器的开发者专注于自己的领域。

因此，这份PEP提出了一个web服务器和web应用或框架之间的简单接口规范，也就是Python Web Server Gateway Interface (WSGI)。

但仅仅存在一个WSGI规范的无助于解决服务器和框架的Python Web应用程序的现有状态。服务器和框架的作者或维护者必须自己实现一份WSGI才能让规范生效。

然而，由于没有现成的服务器或框架支持WSGI，并且对实现WSGI的作者也很少有直接的收获或奖励。因此，WSGI的实现就必须足够简单，最大化的减少实现成本。

因此，在框架和服务器两端实现WSGI的简单性对WSGI来说是至关重要的，这样是任何设计决策的主要依据。

但是请主义，一个作者实现WSGI的简单性和一个用户使用web框架的简单性并不是同一件事。WSGI为框架作者提供一套`no frills`（绝无多余）的接口，因为现有的框架在处理response对象和操作cookie上面是有冲突的。请牢记，WSGI的目标是促进现有的服务器和应用程序或框架容易互连，而不是制造一个新的网络框架。

另外，WSGI不需要除当前版本python之外的任何功能，也不会依赖于任何模块。

除了能轻松实现程序和框架之间的互联，它也应该能轻松的创建请求预处理器、响应后处理器和其他的基于WSGI的中间件的组建（对于服务器来说这些组建是应用程序，对于应用程序来说这些组建是服务器）。

如果中间件可以既简单又健壮，并且WSGI广泛使用于服务器和框架，那么就会有一种全新的Python的Web应用程序框架：一个仅仅由几个松散-耦合（loosely-coupled）的WSGI中间件组成的web框架。事实上，现有的框架作者都偏向于重构现有框架来让框架以这种方式提供服务（就是全新的web应用程序框架），使他们看起来更像是配合使用WSGI的库，而不是整体框架。这让web应用的开发者能自由的选择合适的组合，而不需要把所有的功能都让一个框架提供。

很明显，这一天的到来还遥遥无期，在这期间，一个合理的目标就是让任何框架在任何服务器上运行起来。

最后，应该提及的是，当前版本的WSGI并没有明确的规定一个web应用需要以什么方式部署在web服务器或gateway上。目前，者需要服务器或者gateway来定义和实现。

在有足够多的服务器和框架实现了WSGI并在实践中产生这个需求之后，再创建一份PEP来描述WSGI服务器和应用程序的架构部署标准，想必才是有必要的。

##概览

WSGI接口有两种形式：一种针对服务器或gateway，另一种正对web应用或web框架。服务器调用一个由应用程序提供的可调用对象，至于该对象是如何被调用的就要取决于服务器或者gateway。假定一些服务器或者gateway需要应用程序的部署人员编写一个脚本来起启动服务器或gateway的实例，并把应用程序对象提供给服务器。其他服务器或gateway可以使用配置文件或其他机制来指定应用程序对象该从那里导入或者获取。

除了`pure`（纯）服务器/gateway和web框架/应用，也可以实现创建实现了这份WSGI的中间件。这种中间件对于包含它们的服务器序而言是应用程序，对于它们包含的应用程序而言是服务器，并且diy用来提供扩展的API，内容转换、导航等其他有用的功能。

在整篇文章中，我们使用的属于`可调用`的意思是一个函数、方法、类、或者一个包含`__call__`方法的实例。者依赖于服务器/框架根据自己所需要的技术来选择实现方式。但是，一个服务器/框架调用一个可调用程序的时候不能依赖调用程序的实现方式。可调用程序仅仅是用来调用的，而不是用来自省的（意思是可调用程序跟__call__方法没有关系，只是这里的一个术语）。

##服务器/应用程序端

应用程序对象是一个接收两个参数的可调用对象。这里的`对象`并不是一个真正的对象（python对象），一个函数、方法、类、或者一个包含`__call__`方法的实例可以用作应用程序对象。应用程序对象必须能被多次调用，因为几乎所有的服务器/gateway（除了CGI）都会重复的请求。

（注意：尽管我们把它叫做应用程序对象，但并不是说开发人员要把WSGI当成API来调用。它假定应用程序开发者将继续使用高层次的框架。WSGI只是框架和服务器开发者的一个工具，并不直接面向应用程序开发者。）

如下是应用程序对象的两个例子：

```python
def simple_server(environ, start_response):
    """Simplest possible application object"""
    status = "200 OK"
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return ['Hello world !\n']
```

```python
class AppClass:
    """Produce the same output, but using a class
    注意：AppClass 就是这里的 application，所以调用它的时候会返回AppClass的一个实例，这个实例迭代的返回‘application callable’该返回的对象。
    如果我们想使用AppClass的实例，我们需要实现一个__call__方法，外部通过调用这个方法来执行应用程序，并且我们需要创建一个实例给服务器使用
    """
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response

    def __iter__(self):
        status = "200 OK"
        response_headers = [('Content-type', 'text/plain')]
        self.start_response(status, response_headers)
        yield "Hello world !\n"
```

##服务器/gateway端

每次收到从HTTP客户端来的请求服务器就会调用可调用的应用程序。下面是一个简单的CGI，是以接收一个应用程序对象的函数来实现的。这个例子并没有良好的出错处理，默认情况下未被捕获的错误会输出到`sys.stderr`并被服务器记录

```python
import os, sys

def run_with_cgi(application):

    environ = dict(os.environ.items())
    environ['wsgi.input']        = sys.stdin
    environ['wsgi.errors']       = sys.stderr
    environ['wsgi.version']      = (1, 0)
    environ['wsgi.multithread']  = False
    environ['wsgi.multiprocess'] = True
    environ['wsgi.run_once']     = True

    if environ.get('HTTPS', 'off') in ('on', '1'):
        environ['wsgi.url_scheme'] = 'https'
    else:
        environ['wsgi.url_scheme'] = 'http'

    headers_set = []
    headers_sent = []

    def write(data):
        if not headers_set:
             raise AssertionError("write() before start_response()")

        elif not headers_sent:
             # Before the first output, send the stored headers
             status, response_headers = headers_sent[:] = headers_set
             sys.stdout.write('Status: %s\r\n' % status)
             for header in response_headers:
                 sys.stdout.write('%s: %s\r\n' % header)
             sys.stdout.write('\r\n')

        sys.stdout.write(data)
        sys.stdout.flush()

    def start_response(status, response_headers, exc_info=None):
        if exc_info:
            try:
                if headers_sent:
                    # Re-raise original exception if headers sent
                    raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                exc_info = None     # avoid dangling circular ref
        elif headers_set:
            raise AssertionError("Headers already set!")

        headers_set[:] = [status, response_headers]
        return write

    result = application(environ, start_response)
    try:
        for data in result:
            if data:    # don't send headers until body appears
                write(data)
        if not headers_sent:
            write('')   # send headers now if body was empty
    finally:
        if hasattr(result, 'close'):
            result.close()
```

## 中间件

我们知道有些中间件又能当成服务器又能当成应用程序，这些中间件可以提供这样的一些功能
- 根据目标url将请求传递到不同应用程序对象
- 允许多个应用程序和框架在同一个进程中执行
- 通过在网络上传递请求和响应实现负载均衡和远程处理
- 对内容进行加工

中间件对于服务器和应用程序都是透明的，所以不需要特殊支持。想在应用程序中加入中间件的用户只需要把中间件当成应用程序提供给服务器，并篇日志中间件可以调用应用程序。当然，这里的中间件包裹的“应用程序”可能还还有中间件，层层包裹就形成了所谓的`中间件堆栈`了。

大多数情况下，中间件需要符合服务器端和应用程序端的限制和要求。有时候，中间件的要求会比纯纯服务器和纯应用程序的要求更苛刻，这些点将会在说明书中讲明。

这里有一个中间件组件的例子，它用Joe Strout的piglatin.py将text/plain的响应转换成pig latin（注意：真正的中间件应该使用更加安全的方式——应该检查内容的类型和内容的编码，这个简单的例子还忽略了一个单词跨块进行行分裂的可能性)。

```python
from piglatin import piglatin

class LatinIter:

    """Transform iterated output to piglatin, if it's okay to do so

    Note that the "okayness" can change until the application yields
    its first non-empty string, so 'transform_ok' has to be a mutable
    truth value.
    """

    def __init__(self, result, transform_ok):
        if hasattr(result, 'close'):
            self.close = result.close
        self._next = iter(result).next
        self.transform_ok = transform_ok

    def __iter__(self):
        return self

    def next(self):
        if self.transform_ok:
            return piglatin(self._next())
        else:
            return self._next()

class Latinator:

    # by default, don't transform output
    transform = False

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):

        transform_ok = []

        def start_latin(status, response_headers, exc_info=None):

            # Reset ok flag, in case this is a repeat call
            del transform_ok[:]

            for name, value in response_headers:
                if name.lower() == 'content-type' and value == 'text/plain':
                    transform_ok.append(True)
                    # Strip content-length if present, else it'll be wrong
                    response_headers = [(name, value)
                        for name, value in response_headers
                            if name.lower() != 'content-length'
                    ]
                    break

            write = start_response(status, response_headers, exc_info)

            if transform_ok:
                def write_latin(data):
                    write(piglatin(data))
                return write_latin
            else:
                return write

        return LatinIter(self.application(environ, start_latin), transform_ok)


# Run foo_app under a Latinator's control, using the example CGI gateway
from foo_app import foo_app
run_with_cgi(Latinator(foo_app))
```

## 详细信息

应用程序对象必须接收两个参数，我们把它命名为`environ`和`start_response`（可随意修改），服务器**必须**根据关键字位置（而不是名称）调用应用程序如`result = application(environ, start_response)`。

这里`environ`是一个包含CGI-style环境变量的字典对象，这个对象**必须**是python内建的字典对象（不是子类、UserDict或其他字典对象），应用程序可以自由的修改这个对象。这个字典还必须包含一些必须的WSGI所需要的变量（后文有描述），还可能包含一些服务器特定的变量，这些变量根据下文描述的惯例命名。

`start_response`是一个接收两个必选参数和一个可选参数的可调用对象，我们把者几个参数依次命名为`status`、`response_headers`、`exc_info`（可随意修改命名），调用的时候**必须**根据参数位置调用如`start_response(status, response_headers) `

`status`格式如`999 msg here`的状态码，`response_headers`是一个由如`(header_name, header_value)`的元组组成的列表，它描述了HTTP响应的响应头。`exc_info`将会在下文的 [The start_response() Callable]()、[出错处理]()中讲到，这个参数只有在应用程序捕获出错并且要将错误输出到浏览器的时候才会用到。

`start_response`可调用程序必须返回一个可调用的`write(body_data)`，它接收一个可选参数：一个可以作为HTTP响应体(response body)一部分的字符串。（注意：提供可调用的write()只是为了支持现有的框架必要的输出API，新的框架应尽可能避免使用，详见[Buffering and Streaming]()）

当被调用时，应用程序对象必须返回一个可迭代的0或者多个字符串（yielding zero or more strings）。有很多方法可以实现这个目标，比如返回一个字符串列表，或者应用程序本身是个可以返回字符串的生成器函数(generator function that yield strings)，或者应用程序本身是一个可以产生可迭代对象的类。无论如何实现，应用程序对象都必须返回一个可迭代的0或者多个字符串（yielding zero or more strings）。

服务器必须将产生的的字符串（也就是上文中返回的yielded string）无缓冲的发送给客户端，每次传输完成之后才能取下一个字符串（换句话说，应用程序需要实现自己的缓冲区，[Buffering and Streaming]()阐述了更多关于如何处理输出的问题）

服务器应该把产生的字符串当成字节流处理：特别的是，要确保结束行没被修改（it should ensure that line endings are not altered）。应用程序需要保证字符是以客户端需要的编码输出的。

如果调 len(iterable) 成功，服务器将认为结果是正确的。也就是说，应用程序返回的可迭代的字符串提供了一个有用 的__len__() 方法，么肯定返回了正确的结果。

如果可迭代对象返回了`close()`方法，那么不管这个请求是否成果完成，每次请求结束前服务器都必须调用这个方法（这是用来支持应用程序对象占用资源的释放）。

（注意：应用程序必须在可迭代对象产生第一个字符串之前调用`start_response`，这样服务器才能先发送header再发送body。但是这个过程也可以发生在可迭代对象第一次迭代前，所以服务器不能保证迭代开始前`start_response`已经被调用过了。）

最后，服务器不能直接调用应用程序返回的可迭代对象的其他任何属性，除非这个属性是针对服务器实现的特定实例。

##environ变量

`environ`需要包含如下CGI定义的环境变量。下面的变量必须被呈现出来，除非他的值是空（这时候如果没有特别指出，空值会被忽略）。

- REQUEST_METHOD：HTTP请求的方式，比如 "GET" 或者 "POST"， 这个不能是空字符串并且也是必须给出的字段。
- SCRIPT_NAME：请求URL中路径的开始部分，对应应用程序对象，这样应用程序就知道它的虚拟位置。如果该应用程序对应服务器的根的话， 它可能是为空字符串。
- PATH_INFO：请求URL中路径的剩余部分，指定请求的目标在应用程序内部的虚拟位置。如果请求的目标是应用程序跟并且没有trailing slash的话，可能为空字符串 。
- QUERY_STRING：请求URL中跟在"?"后面的那部分,可能为空或不存在。
- CONTENT_TYPE：HTTP请求中任何 Content-Type 域的内容。
- CONTENT_LENGTH：HTTP请求中任何 Content-Length 域的内容。可能为空或不存在。
- SERVER_NAME , SERVER_PORT ：SCRIPT_NAME和PATH_INFO结合可以产生完整的url。但是，如果HTTP_HOST存在的话，优先使用它代替SCRIIPT_NAME。这两个参数都不能为空。
- SERVER_PROTOCOL ：浏览器返送请求的协议版本（如HTTP/1.0），这将决定应用程序如何处理浏览器发送的headers。
- HTTP_ Variables：以`HTTP_`打头的变量，也就是对应客户端提供的HTTP请求headers。

服务器应该尽可能的提供做够多的其他CGI变量。另外，如果使用了SSL，那服务器还要提供足够多的Apache SSL环境变量。但是，请注意，任何使用比上面列出的其他变量的CGI应用程序必然是不可移植到不支持扩展相关的Web服务器。

注意：不需要的变量一定要移除environ，还有就是CGI定义的变量都是字符串类型（str）。

除了CGI变量之外，`environ`还可以包含操作系统环境变量，下面是必须包含的环境变量。

- wsgi.version：用元组(1,0)表示1.0版本
- wsgi.url_scheme：代表被调用应用程序url的“scheme”字段，通常是"http"或"https"
- wsgi.input：输入流（文件对象），HTTP请求body可以从里面读取
- wsgi.errors：输出流（文件对象），可以将错误写入。这应该是一个文本模式的流，应用程序使用"\n"作为一行的结束，并且假定它可以被服务器转换成正确的行。对许多服务器来说，wsgi.errors是服务器主要的错误日志，也就是说，它也可以是sys.stderr，或者日志文件。
- wsgi.multithread：如果为True，那么应用程序对象就可以在被同一进程中的另一个线程同时调用。
- wsgi.multiprocess：....
- wsgi.run_once：如果为True，服务器将认为应用程序只在它所被包含的进程的生命周期中调用一次。通常，只有在基于CGI的网关中才为True。

最后 environ 字典也可以包含服务器定义的变量。这些变量的名字必须是小写字母、数字、点和下划线，并且应该带一个能唯一代表服务器的前缀。比如， mod_python可能会定义象这样的一些变量:`mod_python.some_variable`.

##输入和错误流

输入和错误流必须支持如下方法

| 方法名        | 流   |  注解  |
| --------   | -----:  | :----:  |
|   read(size)  | input |  1     |
|   readline()     | input     |   1,2  |
|    readlines(int)    |  input      | 1,3   |
|__iter__()|input||
|flush()|error|4|
|write(str)|error||
|writelines(seq)|error||

1. 