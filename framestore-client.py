#! /usr/bin/env/python

import os, re, json, sys, uuid
from time import sleep, asctime
from subprocess import Popen
import atexit

amazon = {
	"instance-id": "http://169.254.169.254/latest/meta-data/instance-id",
	"public-ip": "http://169.254.169.254/latest/meta-data/public-ipv4",
	"hostname": "http://169.254.169.254/latest/meta-data/public-hostname",
	"dynamic": "http://169.254.169.254/latest/dynamic/instance-identity/document",
	"user-data": "http://169.254.169.254/latest/user-data"
}

machine_id = os.popen("curl -s " + amazon['instance-id']).read().strip()

def log(string):
	msg = "[ %s ] [ %s ] %s" % (asctime(), machine_id, string)
	sys.stderr.write(msg + "\n")

base = "badaboom"

cmd = "curl -s %s | grep base=" % amazon['user-data']
userbase = os.popen(cmd).read().strip()
if userbase:
	base = userbase.split("=")[1]
else:
	log("WARNING: Using default Firebase: " + base)

base = "https://%s.firebaseio-demo.com" % base
framestoreBase = base + '/framestores.json'
try:
	meta = json.loads(os.popen("curl -s " + amazon['dynamic']).read().strip())
	zone = meta['availabilityZone']
except ValueError:
	log("FATAL: Amazon metadata error.")
	exit(1)

pidfile = "/var/run/framestore-client.pid"
os.popen("echo %s > %s" % (os.getpid(), pidfile)).read()

log("Framestore client started (%s). Monitoring base @ %s" % (os.getpid(), base))

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
	framestores = json.loads(os.popen("curl -s %s" % framestoreBase).read().strip())
	online = {}
	if framestores:
		log("Discovered " + str(len(framestores.items())) + " framestore(s).")
		for instance_id in framestores.keys():
			if instance_id!=machine_id:
				machine = framestores[instance_id]
				if machine.has_key('filesystems'):
					for fs_name in machine['filesystems'].keys():
						fs_details = machine['filesystems'][fs_name]
						if fs_details.has_key('status') \
							and machine.has_key('private_ip') \
							and machine.has_key('public_ip'):
							status = fs_details['status']
							private_ip = machine['private_ip']
							public_ip = machine['public_ip']
							if status=='online' and fs_details.has_key('mount'):
								remoteMountPath = fs_details['mount']
								privateHostPath = private_ip + ":" + remoteMountPath
								publicHostPath = public_ip + ":" + remoteMountPath
								isMounted = os.popen("mount | grep " + remoteMountPath).read().strip()
								if not isMounted:
									if not os.path.exists(remoteMountPath):
										os.mkdir(remoteMountPath)
									if zone==machine['zone']:
										mountNfs(privateHostPath)
									else:
										mountNfs(publicHostPath)
								else:
									touchDir = remoteMountPath + "/.connected"
									touchFile = touchDir + "/" + machine_id
									if os.path.exists(touchDir):
										touch(touchFile)
									log("Already mounted: " + isMounted)

								online[privateHostPath] = machine
								online[publicHostPath] = machine

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