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

def mountNfs(hostPath):
	cmd = "mount.nfs4 " + hostPath + " " + remoteMountPath
	proc = Popen(cmd, shell=True)
	sleep(10)
	if proc.poll() is None:
		proc.kill()
		return False
	else:
		return True


while 1:
	framestores = json.loads(os.popen("curl -s %s" % framestoreBase).read().strip())
	online = {}
	if framestores:
		for (instance_id, data) in framestores.items():
			if data.has_key('status') and data.has_key('private_ip') and data.has_key('public_ip'):
				status = data['status']
				private_ip = data['private_ip']
				public_ip = data['public_ip']
				if status=='online' and data.has_key('mountedAt'):
					remoteMountPath = data['mountedAt']
					hostPath = private_ip + ":" + remoteMountPath
					isMounted = os.popen("mount | grep " + remoteMountPath).read().strip()
					if not isMounted:
						if not os.path.exists(remoteMountPath):
							os.mkdir(remoteMountPath)
						mounted = mountNfs(hostPath)
						if not mounted:
							hostPath = public_ip + ":" + remoteMountPath
							mountNfs(hostPath)
					online[private_ip] = data
					online[public_ip] = data
				elif status=='offline':
					[online.__delitem__(ip) for ip in (private_ip, public_ip) if online.has_key(ip)]

	mounted = [l.strip().split() for l in os.popen("mount").readlines() if re.search("media",l) and re.search("nfs",l)]
	for mount in mounted:
		host_ip = mount[0].split(":")[0]
		localMountPoint = mount[2]
		if host_ip not in online.keys():
			cmd = "umount.nfs4 " + localMountPoint + " -fl"
			os.popen(cmd).read().strip()

	sleep(10)