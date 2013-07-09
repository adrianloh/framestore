#! /usr/bin/env/python

import os, re, json
from time import sleep
from subprocess import Popen
import atexit

base = "https://badabing.firebaseio-demo.com"
framestoreBase = base + '/framestores.json'

@atexit.register
def removeBase():
	pass

while 1:
	framestores = json.loads(os.popen("curl -s %s" % framestoreBase).read().strip())
	online = []
	if framestores:
		for (instance_id, data) in framestores.items():
			if data.has_key('status') \
				and (data['status']=='online') \
				and data.has_key('mountedAt') \
				and data.has_key('private_ip') \
				and data.has_key('public_ip'):
				remoteMountPath = data['mountedAt']
				ip = data['private_ip']
				isMounted = os.popen("mount | grep " + remoteMountPath).read().strip()
				hostPath = ip + ":" + remoteMountPath
				if not isMounted:
					if not os.path.exists(remoteMountPath):
						os.mkdir(remoteMountPath)
					cmd = "mount -t nfs " + hostPath + " " + remoteMountPath
					proc = Popen(cmd, shell=True)
					sleep(10)
					if proc.poll() is None:
						proc.kill()
				online.append(hostPath)

	mounted = [l.strip().split() for l in os.popen("mount").readlines() if re.search("media",l) and re.search("nfs",l)]
	for mount in mounted:
		hostPath = mount[0]
		localMountPoint = mount[2]
		if hostPath not in online:
			cmd = "umount.nfs4 " + localMountPoint + " -fl"
			os.popen(cmd).read().strip()

	sleep(10)