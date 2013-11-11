import unittest, threading, time

from twisted.internet import reactor, threads
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from Queue import Queue

import envy

reactor_sem = threading.Semaphore(0)

def reactor_thread():
	def reactor_running():
		reactor_sem.release()

	reactor.callLater(0, reactor_running)
	reactor.run(installSignalHandlers=False)


class IO(object):
	queue = Queue()

	def __init__(self, *args, **kwds):
		self.args = args
		self.kwds = kwds

		self.queue.put(self)

	@classmethod
	def next(cls):
		return cls.queue.get()


class AsyncIO(IO):
	def wait(self):
		self.deferred = Deferred()
		return self.deferred

	def callback(self, value):
		self.deferred.callback(value)

	def errback(self, failure):
		self.deferred.errback(failure)


class BlockingIO(IO):
	def __init__(self, *args, **kwds):
		self._lock = threading.Lock()

		self._resolved_cv = threading.Condition(self._lock)
		self._got_result = self._got_failure = False

		IO.__init__(self, *args, **kwds)

	def wait(self):
		with self._lock:
			while not self._got_result and not self._got_failure:
				self._resolved_cv.wait()

			if self._got_result:
				return self._result
			else:
				raise self._failure

	def callback(self, result):
		with self._lock:
			self._got_result = True
			self._result = result
			self._resolved_cv.notify()

	def errback(self, failure):
		with self._lock:
			self._got_failure = True
			self._failure = failure
			self._resolved_cv.notify()


def blocking_function(*args, **kwds):
	io = BlockingIO(*args, **kwds)
	return io.wait()



class EnvyTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		t = threading.Thread(group=None,
		     	             name="Reactor thread",
			                 target=reactor_thread)
		t.setDaemon(True)
		t.start()
		reactor_sem.acquire()

	
	def test_nothing(self):
		print "First testcase"



	def test_something(self):
		print "Another testcase"

	@classmethod
	def tearDownClass(cls):
		reactor.stop()

		# Give the reactor time to stop. 
		time.sleep(0.1)