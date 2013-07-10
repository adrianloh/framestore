#! /usr/bin/env/python

import os, re, json, sys
from time import sleep, asctime
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

framestoreBase = base + '/framestores'
meta = json.loads(os.popen("curl -s 169.254.169.254/latest/dynamic/instance-identity/document/").read().strip())
instance_id = meta['instanceId']
private_ip = meta['privateIp']
zone = meta['availabilityZone']
dob = meta['pendingTime']

public_ip = os.popen("curl -s http://169.254.169.254/latest/meta-data/public-ipv4").read().strip()
hostname = os.popen("curl -s http://169.254.169.254/latest/meta-data/public-hostname").read().strip()

machineBase = framestoreBase + '/' + instance_id

stat = {
	'public_ip': public_ip,
	'private_ip': private_ip,
	'hostname': hostname,
    'zone': zone,
	'status': 'offline'
}

cmd = """curl -sX PUT -d '%s' %s""" % (json.dumps(stat), machineBase + ".json")
os.popen(cmd).read()
log("Server " + hostname + " is up @ " + private_ip + ". Broadcasting presence to " + base)


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
	log("RAID name: " + json.dumps(raidName))
	if len(raidName.split(":"))>1:
		raidName = raidName.split(":")[-1].split(" ")[0]
	else:
		return None
	if re.match("^\d+$", raidName) or len(raidName)==0:
		return None
	else:
		return raidName

def exportNfs(mountPath):
	nfs_status = os.popen("service nfs status").read().strip()
	started = re.search("running", nfs_status)
	if not started:
		os.popen("service nfs start").read().strip()
		sleep(5)
	if os.popen("exportfs -v | grep " + mountPath).read().strip():
		sleep(2)
		setStatus("online")
	else:
		setStatus("ready")
		cmd = "cat /etc/exports | grep " + mountPath
		shared = os.popen(cmd).read().strip()
		if not shared:
			cmd = """echo "%s  *(rw,async,no_root_squash)" >> /etc/exports""" % mountPath
			os.popen(cmd).read().strip()
		os.popen("exportfs -ar").read().strip()
		sleep(5)
		exportNfs(mountPath)


def countFile(path):
	return int(os.popen("find %s -type f | wc -l" % path).read().strip())


while 1:
	raidReady = os.popen("fdisk -l | grep /dev/md").read().strip()
	if raidReady:
		raidPath = re.findall("/dev/md\d+", raidReady)[0]
		raidName = mdadmName(raidPath)
		if raidName:
			mountPath = "/media/" + raidName
			isMounted = os.popen("mount | grep " + mountPath).read().strip()
			log("RAID " + raidPath + " detected.")
			keys = ['devicePath', "available", "usedSpace", "freeSpace", "usedPercent", "mount"]
			if isMounted:
				log("RAID " + raidPath + " mounted at " + mountPath)
				res = os.popen("df -h | grep md").read().strip()
				if res:
					data = res.split()
					h = dict(zip(keys, data))
					h['files'] = countFile(mountPath)
					patchData(h)
				exportNfs(mountPath)
			else:
				log("Mounting RAID " + raidPath + " to " + mountPath)
				if not os.path.exists(mountPath):
					os.mkdir(mountPath)
				cmd = "mount -t xfs " + raidPath + " " + mountPath
				setStatus("mounting")
				os.popen(cmd).read().strip()
	else:
		setStatus("offline")
		data = [None for k in keys]
		h = dict(zip(keys, data))
		patchData(h)

	sleep(6)