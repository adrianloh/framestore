#! /usr/bin/env/python

import os, re, json, sys, uuid
from time import sleep, asctime
from subprocess import Popen
import atexit

def log(string):
	msg = "[ %s ] %s" % (asctime(), string)
	sys.stderr.write(msg + "\n")

base = "https://badabing.firebaseio-demo.com"

try:
	userData = json.loads(os.popen("curl -s http://169.254.169.254/latest/user-data").read().strip())
	if isinstance(userData, dict) and userData.has_key('base'):
		base = userData['base']
except ValueError: pass

framestoreBase = base + '/framestores.json'
machine_id = os.popen("curl -s http://169.254.169.254/latest/meta-data/instance-id").read().strip()
meta = json.loads(os.popen("curl -s 169.254.169.254/latest/dynamic/instance-identity/document/").read().strip())
zone = meta['availabilityZone']

pidfile = "/var/run/framestore_client.pid"
with open(pidfile, 'w') as f:
	f.write(str(os.getpid()))

@atexit.register
def removeBase():
	pass

def mountNfs(hostPath):
	cmd = "mount.nfs4 " + hostPath + " " + remoteMountPath
	log(cmd)
	proc = Popen(cmd, shell=True)
	sleep(10)
	if proc.poll() is None:
		proc.kill()
		return False
	else:
		return True

def touch(fname):
	try:
		if os.path.exists(fname):
			os.utime(fname, None)
		else:
			with open(fname, 'w') as f:
				f.write("")
	except (OSError, IOError): pass

while 1:
	touch(pidfile)
	framestores = json.loads(os.popen("curl -s %s" % framestoreBase).read().strip())
	online = {}
	if framestores:
		framestores = framestores.items()
		log("Discovered " + str(len(framestores)) + " framestores.")
		for (instance_id, data) in framestores:
			log(json.dumps(data))
			if instance_id!=machine_id \
				and data.has_key('status') \
				and data.has_key('private_ip') \
				and data.has_key('public_ip'):
				status = data['status']
				private_ip = data['private_ip']
				public_ip = data['public_ip']
				if status=='online' and data.has_key('mount'):
					remoteMountPath = data['mount']
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
					else:
						touchDir = remoteMountPath + "/connected"
						touchFile = touchDir + "/" + machine_id
						if os.path.exists(touchDir):
							touch(touchFile)
						log("Already mounted: " + isMounted)

					online[privateHostPath] = data
					online[publicHostPath] = data

	mounted = [l.strip().split() for l in os.popen("mount").readlines() if re.search("media",l) and re.search("nfs",l)]
	for mount in mounted:
		hostPath = mount[0]
		localMountPoint = mount[2]
		if hostPath not in online.keys():
			cmd = "umount.nfs4 " + localMountPoint + " -fl"
			log(cmd)
			os.popen(cmd).read().strip()
			newdir = os.path.split(localMountPoint)[0] + "/trash_" + uuid.uuid4().hex
			os.rename(localMountPoint, newdir)
	touch(pidfile)
	sleep(10)