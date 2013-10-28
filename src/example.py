from twisted.internet import reactor, threads
import envy


def outer():
	print "Calling inner"
	d = inner()
	print "Called inner"

	def callback(ignored):
		print "All done"

	d.addCallback(callback)

@envy.make_async
def inner():
	print "Not slept at all"
	envy.sleep(1)
	print "Slept once"
	envy.sleep(1)
	print "Slept twice"
	envy.sleep(1)
	print "Slep three times!"


reactor.callLater(0, outer)
reactor.run()