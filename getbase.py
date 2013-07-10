#! /usr/bin/env/python

import os, json

base = "https://badabing.firebaseio-demo.com"

try:
	userData = json.loads(os.popen("curl -s http://169.254.169.254/latest/user-data").read().strip())
	if isinstance(userData, dict) and userData.has_key('base'):
		base = userData['base']
except ValueError: pass

print base