#! /usr/bin/env/python

import os, re, json
from time import sleep
from subprocess import Popen
import atexit

base = "https://badabing.firebaseio-demo.com"
framestoreBase = base + '/framestores.json'
machine_id = os.popen("curl -s http://169.254.169.254/latest/meta-data/instance-id").read().strip()
zone = os.popen("ec2-metadata -z | awk '{print $2}'").read().strip()

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
			if instance_id!=machine_id and data.has_key('status') and data.has_key('private_ip') and data.has_key('public_ip'):
				status = data['status']
				private_ip = data['private_ip']
				public_ip = data['public_ip']
				if status=='online' and data.has_key('mountedAt'):
					remoteMountPath = data['mountedAt']
					privateHostPath = private_ip + ":" + remoteMountPath
					publicHostPath = public_ip + ":" + remoteMountPath
					isMounted = os.popen("mount | grep " + remoteMountPath).read().strip()
					if not isMounted:
						if not os.path.exists(remoteMountPath):
							os.mkdir(remoteMountPath)
						if zone==data['zone']:
							mountNfs(privateHostPath)
						else:
							mountNfs(publicHostPath)
					online[private_ip] = data
					online[public_ip] = data

	mounted = [l.strip().split() for l in os.popen("mount").readlines() if re.search("media",l) and re.search("nfs",l)]
	for mount in mounted:
		hostPath = mount[0]
		localMountPoint = mount[2]
		if hostPath not in online.keys():
			cmd = "umount.nfs4 " + localMountPoint + " -fl"
			os.popen(cmd).read().strip()

	sleep(10)