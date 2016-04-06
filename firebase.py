# a client for connecting to firebase + performing streaming.
# compatible with app engine bc that is what i needed this for
# enjoy 
#
# Written by Justin Brower, code adopted from https://github.com/firebase/EventSource-Examples/blob/master/python/chat.py
import json
from sseclient import SSEClient
from Queue import Queue
import requests
import json
import threading
import socket
import sys


class Firebase:
	"""
	Implement the streaming part of the firebase REST API.
	"""
	# A mapping from endpoints -> sseclients.
	connections = dict()

	def __init__(self, secret, baseURL, path="/"):
		self.secret = secret
		self.baseURL = baseURL
		self.path = path

	def _construct_url(self):
		return self.baseURL + self.path + ".json?auth=" + self.secret

	def child(self, path):
		newPath = self.path + path + "/"
		return Firebase(self.secret, self.baseURL, path=newPath)

	def setAddListener(self, callback):
		"""
		Sets the listener to be fired when a node is added to this level.
		"""
		if not callback:
			callback = lambda x,y: None
		if not self.path in Firebase.connections:
			# this path didn't even exist.
			Firebase.connections[self.path] = RemoteThread(self._construct_url(), callback, None)
			Firebase.connections[self.path].start()
		else:
			# change the callback function?
			Firebase.connections[self.path].callback = callback
	def setRemoveListener(self, callback):
		"""
		Sets the listener to be fired when a node is removed from this level.
		"""
		if not callback:
			callback = lambda x: None
		if not self.path in Firebase.connections:
			# this path didn't even exist.
			Firebase.connections[self.path] = RemoteThread(self._construct_url(), None, callback)
			Firebase.connections[self.path].start()
		else:
			# change the callback function?
			Firebase.connections[self.path].deleteCallback = callback
	def closeListener(self):
		"""
		Closes the add/delete listeners at a given firebase node.
		"""
		if self.path in Firebase.connections:
			Firebase.connections[self.path].closeQuietly()
			del Firebase.connections[self.path]

	def closeAllListeners(self):
		"""
		Closes all the listeners on the firebase database. At all levels. All of em.
		"""
		for path in Firebase.connections:
			Firebase.connections[path].closeQuietly()
			del Firebase.connections[path]

	def delete(self):
		"""
		deletes the firebase node at the current path.
		"""
		r = requests.delete(self._construct_url())
		return r.status_code == 200

class ClosableSSEClient(SSEClient):
    """
    Hack in some closing functionality on top of the SSEClient
    """

    def __init__(self, *args, **kwargs):
        self.should_connect = True
        super(ClosableSSEClient, self).__init__(*args, **kwargs)

    def _connect(self):
        if self.should_connect:
            super(ClosableSSEClient, self)._connect()
        else:
            raise StopIteration()

    def close(self):
        self.should_connect = False
        self.retry = 0
        # HACK: dig through the sseclient library to the requests library down to the underlying socket.
        # then close that to raise an exception to get out of streaming. I should probably file an issue w/ the
        # requests library to make this easier
        self.resp.raw._fp.fp._sock.shutdown(socket.SHUT_RDWR)
        self.resp.raw._fp.fp._sock.close()


class RemoteThread(threading.Thread):

    def __init__(self, url, callback, deleteCallback):
        self.url = url
        self.callback = (callback or (lambda x,y: None))
        self.deleteCallback = (deleteCallback or (lambda x: None))
        self.closeOnNextIteration = False
        super(RemoteThread, self).__init__()

    def closeQuietly():
    	self.closeOnNextIteration = True

    def run(self):
        try:
            print "Connecting to URL: " + self.url
            self.sse = ClosableSSEClient(self.url)
            for msg in self.sse:
            	if self.closeOnNextIteration:
            		self.close()
            		return
            	# bad authentication / security responses
                if msg.event == "auth_revoked":
                	print "Authentication revoked: Killing thread."
                	return
                if msg.event == "cancel":
                	print "Security Error: Killing thread."
                	return
            	if not msg.data:
            		continue

                msg_data = json.loads(msg.data)
                if msg_data is None:    # keep-alives
                    continue
                path = msg_data['path']
                data = msg_data['data']
                print "MSG TYPE:" + msg.event
                print "MSG DATA: " + msg.data
                if data:
                	self.callback(path, data)
                else:
                	self.deleteCallback(path)
        except socket.error:
            pass    # this can happen when we close the stream

    def close(self):
        if self.sse:
            self.sse.close()

def addHandler(path, data):
	print "Path: " + str(path)
	print "Data: " + str(data)
	if path == "/":
		# loaded multiple
		for key in data:
			f.child('test').child(key).delete()
			print "[initial] Request to: " + data[key]["to"]
	elif path.count("/") == 1:
		# loaded single
		print "[added] Request to: " + data["to"]
		f.child('test').child(path[1:]).delete()

def deleteHandler(path):
	if path == "/":
		# loaded multiple
		print "Deleted several"
	elif path.count("/") == 1:
		# loaded single
		print "Deleted " + path[1:]


def main():
	# fill these in
	APP_KEY = "appkey"
	APP_URL = "https://myproject.firebaseio.com"
	f = Firebase(APP_KEY, APP_URL)
	f.child('test').setAddListener(addHandler)
	f.child('test').setRemoveListener(deleteHandler)

if __name__ == "__main__":
	main()