#! /usr/bin/env/python

import os, re, json, sys
from time import sleep, asctime, time
import atexit

amazon = {
	"instance-id": "http://169.254.169.254/latest/meta-data/instance-id",
	"public-ip": "http://169.254.169.254/latest/meta-data/public-ipv4",
    "hostname": "http://169.254.169.254/latest/meta-data/public-hostname",
    "dynamic": "http://169.254.169.254/latest/dynamic/instance-identity/document",
	"user-data": "http://169.254.169.254/latest/user-data"
}

instance_id = os.popen("curl -s "+ amazon['instance-id']).read().strip()
public_ip = os.popen("curl -s " + amazon['public-ip']).read().strip()
hostname = os.popen("curl -s " + amazon['hostname']).read().strip()

def log(string):
	msg = "[ %s ][ %s ] %s" % (asctime(), instance_id, string)
	sys.stderr.write(msg + "\n")

try:
	meta = json.loads(os.popen("curl -s " + amazon['dynamic']).read().strip())
	private_ip = meta['privateIp']
	zone = meta['availabilityZone']
	dob = meta['pendingTime']
except ValueError:
	log("FATAL: Amazon metadata error.")
	exit(1)

base = "https://badabing.firebaseio-demo.com"

try:
	userData = json.loads(os.popen("curl -s " + amazon['user-data']).read().strip())
	if isinstance(userData, dict) and userData.has_key('base'):
		base = userData['base']
	else:
		raise ValueError
except ValueError:
	log("WARNING: Using default Firebase: " + base)

framestoreBase = base + '/framestores'
machineBase = framestoreBase + '/' + instance_id
stat = {
	'public_ip': public_ip,
	'private_ip': private_ip,
	'hostname': hostname,
	'zone': zone,
	'status': 'offline'
}

cmd = """curl -sX PUT -d '%s' %s""" % (json.dumps(stat), machineBase + ".json")
res = os.popen(cmd).read()
if res and not re.match("error", res):
	log("Server " + hostname + " is up @ " + private_ip + ". Broadcasting presence to " + base)
else:
	log("FATAL: Failed broadcast to Firebase: " + base)
	exit(1)

pidfile = "/var/run/framestore.pid"
with open(pidfile, 'w') as f:
	f.write(str(os.getpid()))


@atexit.register
def removeBase():
	cmd = "curl -X DELETE %s" % machineBase + ".json"
	os.popen(cmd).read()


def setData(key, value):
	base = machineBase + "/" + key + ".json"
	cmd = """curl -sX PUT -d '%s' %s""" % (json.dumps(value), base)
	os.popen(cmd).read()


def patchData(value):
	base = machineBase + ".json"
	cmd = """curl -sX PATCH -d '%s' %s""" % (json.dumps(value), base)
	os.popen(cmd).read()


def deleteData(key):
	base = machineBase + "/" + key + ".json"
	cmd = """curl -sX DELETE %s""" % base
	os.popen(cmd).read()


def setStatus(status):
	setData('status', status)


def mdadmName(dev):
	cmd = "mdadm --detail %s | grep Name" % dev
	raidName = os.popen(cmd).read().strip()
	if len(raidName.split(":")) > 1:
		raidName = raidName.split(":")[-1].strip().split(" ")[0]
	else:
		return None
	if re.match("^\d+$", raidName) or len(raidName) == 0:
		return None
	else:
		return raidName


def exportNfs(mountPath):
	nfs_status = os.popen("service nfs status").read().strip()
	started = re.search("running", nfs_status)
	if not started:
		log("NFS service is down. Restarting...")
		res = os.popen("for serv in rpcbind nfs nfslock; do service ${serv} start; done").read().strip()
		if not re.search("OK", res):
			log("WARNING: NFS service failed to start.")
		sleep(5)
	nfs_listening = os.popen("netstat -vat | grep nfs.*LISTEN").read().strip()
	nfs_exporting = os.popen("exportfs -v | grep " + mountPath).read().strip()
	if nfs_listening and nfs_exporting:
		log("NFS share is online: " + mountPath)
		sleep(2)
		setStatus("online")
	else:
		setStatus("ready")
		cmd = "cat /etc/exports | grep " + mountPath
		shared = os.popen(cmd).read().strip()
		if not shared:
			log("Exporting NFS share: " + mountPath)
			cmd = """echo "%s  *(rw,async,no_root_squash)" >> /etc/exports""" % mountPath
			os.popen(cmd).read().strip()
		os.popen("exportfs -ar").read().strip()
		sleep(5)
		exportNfs(mountPath)


def countFile(path):
	return int(os.popen("find %s -type f | wc -l" % path).read().strip())


def touch(fname):
	try:
		if os.path.exists(fname):
			os.utime(fname, None)
		else:
			with open(fname, 'w') as f:
				f.write("")
	except (OSError, IOError):
		pass

while 1:
	touch(pidfile)
	raidReady = os.popen("fdisk -l | grep /dev/md").read().strip()
	if raidReady:
		raidPath = re.findall("/dev/md\d+", raidReady)[0]
		raidName = mdadmName(raidPath)
		keys = ['device', "capacity", "usedSpace", "free", "usedPercent", "mount"]
		if raidName:
			mountPath = "/media/" + raidName
			isMounted = os.popen("mount | grep " + mountPath).read().strip()
			log("RAID present: " + raidPath)
			if isMounted:
				touchDir = mountPath + "/connected/"
				if not os.path.exists(touchDir):
					os.mkdir(touchDir)
				log("RAID mounted: " + mountPath)
				# netstat -vat | grep nfs.*ESTABLISHED
				connected = [f for f in os.listdir(touchDir) if os.path.isfile(touchDir + f) and time() - os.path.getmtime(touchDir + f) < 60]
				res = os.popen("df -h | grep md").read().strip()
				if res:
					data = res.split()
					publish = dict(zip(keys, data))
					publish['clients'] = len(connected)
					publish['files'] = countFile(mountPath)
					patchData(publish)
				exportNfs(mountPath)
			else:
				log("Mounting RAID " + raidPath + " to " + mountPath)
				if not os.path.exists(mountPath):
					os.mkdir(mountPath)
				cmd = "mount " + raidPath + " " + mountPath
				setStatus("mounting")
				os.popen(cmd).read().strip()
	else:
		log("No RAID devices found.")
		setStatus("offline")
		data = [None for k in keys]
		h = dict(zip(keys, data))
		patchData(h)

	touch(pidfile)
	sleep(6)