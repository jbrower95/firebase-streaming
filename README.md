# firebase-streaming
Streaming Firebase Implementation in Python

Usage:
```python
APP_KEY = "appkey"
APP_URL = "https://myproject.firebaseio.com"
f = Firebase(APP_KEY, APP_URL)
f.child('test').setAddListener(addHandler)
f.child('test').setRemoveListener(deleteHandler)
```

Add listeners take two arguments: (path, data). Path is the relative path to the current node, and data is the updated data.
Delete listeners take one argument: the path deleted. This is the relative path from the current node.

This only supports authenticating with the app secret. But what else do you really need for your backend server?

