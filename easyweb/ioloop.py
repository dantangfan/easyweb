#!/usr/bin/env python
# coding:utf-8

import select

POLL_TIMEOUT = 10

POLL_NULL = 0x00
POLL_IN = 0x01
POLL_OUT = 0x04
POLL_ERR = 0x08
POLL_HUP = 0x10
POLL_NVAL = 0x20


class KqueueLoop(object):
    pass


class SelectLoop(object):
    """ make select more like epoll

    We define the functions in epoll to make it much easier to use select
    where their is no epoll on che current platform
    """
    def __init__(self):
        self.__r_list = list()
        self.__w_list = list()
        self.__x_list = list()

    def close(self):
        pass

    def fileno(self):
        pass

    def modify(self, fd, mode):
        self.unregister(fd)
        self.register(fd, mode)

    def poll(self, timeout):
        r, w, x = select.select(self.__r_list, self.__w_list, self.__x_list, timeout)
        result = dict()
        for pare in [(r, POLL_IN), (w, POLL_OUT), (x, POLL_ERR)]:
            for fd in pare[0]:
                result[fd] = pare[1]
        return result.items()

    def register(self, fd, mode):
        if mode & POLL_IN:
            self.__r_list.append(fd)
        elif mode & POLL_OUT:
            self.__w_list.append(fd)
        elif mode & POLL_ERR:
            self.__x_list.append(fd)

    def unregister(self, fd):
        if fd in self.__r_list:
            self.__r_list.remove(fd)
        elif fd in self.__w_list:
            self.__w_list.remove(fd)
        elif fd in self.__x_list:
            self.__x_list.remove(fd)


class IOLoop(object):
    def __init__(self):
        if hasattr(select, "epoll"):
            self.__poll = select.epoll()
            self.__poll_method = "epoll"
        else:
            self.__poll = SelectLoop()
            self.__poll_method = "select"
        self.__fd_handler_map = dict()  # {fd:(sock, handler),...}
        self.__stop = False

    @staticmethod
    def instance():
        if not hasattr(IOLoop, '__instance'):
            IOLoop.__instance = IOLoop()
        return IOLoop.__instance

    def add_handler(self, f, mode, handler):
        # handler is a function like: def func(sock ,fd ,event)
        fd = f.fileno()
        self.__fd_handler_map[fd] = (f, handler)
        self.__poll.register(fd, mode)

    def remove_handler(self, f):
        fd = f.fileno()
        del self.__fd_handler_map[fd]
        self.__poll.unregister(fd)

    def modify(self, f, mode):
        fd = f.fileno()
        self.__poll.modify(fd, mode)

    def poll(self, timeout):
        event_pare = self.__poll.poll(timeout)
        return [(self.__fd_handler_map[fd][0], self.__fd_handler_map[fd][1], fd, event) for fd, event in event_pare]

    def start(self):
        event_pares = None
        while not self.__stop:
            try:
                event_pares = self.poll(POLL_TIMEOUT)
            except (IOError, OSError, SystemError, select.error) as e:
                print e
                continue

            for sock, handler, fd, event in event_pares:
                if handler:
                    try:
                        handler(sock, fd, event)
                    except (OSError, SystemError, IOError) as e:
                        print e
                        continue

    def stop(self):
        self.__stop = True

    def __del__(self):
        if self.__poll:
            self.__poll.close()


def test():
    pass
