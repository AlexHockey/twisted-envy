import unittest, threading

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
		print "Testcase"

	def test_something(self):
		print "Another testcase"

	@classmethod
	def tearDownClass(cls):
		reactor.stop()