from twisted.internet import reactor, threads
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

import functools
import greenlet
import sys


def make_sync(func):
    @functools.wraps(func)
    def wrapper(*pos, **kwds):
        d = func(*pos, **kwds)
        return _wait_one(d)
    return wrapper


def make_async(func):
    @functools.wraps(func)
    def wrapper(*pos, **kwds):
        d = Deferred()

        def greenlet_func():
            try:
                rc = func(*pos, **kwds)
                d.callback(rc)
            except Exception:
                typ, val, tb = sys.exc_info()
                d.errback(Failure(val, typ, tb))

        g = greenlet.greenlet(greenlet_func)
        g.switch()

        return d
    return wrapper


def make_nonblocking(func):
    @make_sync
    @functools.wraps(func)
    def wrapper(*pos, **kwds):
        return threads.deferToThread(func, *pos, **kwds)

    return wrapper


def sleep(t):
    g = greenlet.getcurrent()
    reactor.callLater(t, g.switch)
    g.parent.switch()


class TimeoutException(Exception):
    pass


def timeout(delay):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*pos, **kwds):
            g = greenlet.getcurrent()

            def on_timeout():
                to = TimeoutException("%s did not complete after %f seconds" %
                                      (func.__name__, delay))
                g.throw(to)

            timer = reactor.callLater(delay, on_timeout)

            try:
                rc = func(*pos, **kwds)
            finally:
                if timer.active():
                    timer.cancel()

            return rc
        return wrapper
    return decorator


def interface_decorator(methods, method_decorator):
    def decorator(cls):
        for m in methods:
            attr = getattr(cls, m, None)
            if callable(attr):
                setattr(cls, m, method_decorator(attr))
        return cls
    return decorator


def make_async_interface(methods):
    return interface_decorator(methods, make_async)


def make_sync_interface(methods):
    return interface_decorator(methods, make_sync)


def InterfaceMetaclassFactory(methods, method_decorator):
    class InterfaceMeta(type):
        def __new__(cls, name, bases, dct):
            for m in methods:
                attr = dct.get(m)
                if callable(attr):
                    dct[m] = method_decorator(attr)

            return type.__new__(cls, name, bases, dct)
    return InterfaceMeta


def AsyncInterfaceMetaclassFactory(methods):
    return InterfaceMetaclassFactory(methods, make_async)


def SyncInterfaceMetaclassFactory(methods):
    return InterfaceMetaclassFactory(methods, make_sync)


def run_async(func, *pos, **kwds):
    func = make_async(func)
    return func(*pos, **kwds)


def wait(deferred_or_list):
    if isinstance(deferred_or_list, Deferred):
        return _wait_one(deferred_or_list)
    else:
        return _wait_many(deferred_or_list)

def _ignore_greenlet_exit(func):
    @functools.wraps(func)
    def wrapper(*pos, **kwds):
        try:
            rc = func(*pos, **kwds)
            return rc
        except greenlet.GreenletExit:
            pass

    return wrapper

def _wait_one(d):
    g = greenlet.getcurrent()
    active = True

    @_ignore_greenlet_exit
    def callback(result):
        if not active:
            rc = g.switch(result)
        else:
            reactor.callLater(0, g.switch, result)

    @_ignore_greenlet_exit
    def errback(failure):
        typ, val, tb = failure.type, failure.value, failure.tb
        if not active:
            g.throw(typ, val, tb)
        else:
            reactor.callLater(0, g.throw, typ, val, tb)

    d.addCallbacks(callback, errback)

    active = False
    rc = g.parent.switch()
    return rc


def _wait_many(deferreds):
    for d in deferreds:
        yield _wait_one(d)


def parallelize(funcs):
    deferreds = [f() for f in funcs]
    return _wait_many(deferreds)


def map(func, sequence):
    x = map(lambda elem: functools.partial(func, elem), sequence)
    return parallelize(x)
