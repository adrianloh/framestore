#! /usr/bin/env/python

import os, re, json
from time import sleep

base = "https://badabing.firebaseio-demo.com"
framestoreBase = base + '/framestores'

instance_id = os.popen("curl -s http://169.254.169.254/latest/meta-data/instance-id").read().strip()
public_ip = os.popen("curl -s http://169.254.169.254/latest/meta-data/public-ipv4").read().strip()
private_ip = os.popen("curl -s http://169.254.169.254/latest/meta-data/local-ipv4").read().strip()
hostname = os.popen("curl -s http://169.254.169.254/latest/meta-data/public-hostname").read().strip()
machineBase = framestoreBase + '/' + instance_id
stat = {
	'public_ip': public_ip,
	'private_ip': private_ip,
	'hostname': hostname
}
cmd = """curl -sX PUT -d '%s' %s""" % (json.dumps(stat), machineBase + ".json")
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

while 1:
	mountPath = "/media/framestore"
	isMounted = os.popen("mount | grep " + mountPath).read().strip()
	keys = ['devicePath', "available", "usedSpace", "freeSpace", "usedPercent", "mountedAt"]
	if isMounted:
		setStatus("online")
		res = os.popen("df -h | grep md").read().strip()
		if res:
			data = res.split()
		else:
			data = [None for k in keys]
			setStatus("offline")
		h = dict(zip(keys, data))
		patchData(h)
		sleep(10)
	else:
		setStatus("offline")
		raidReady = os.popen("sudo fdisk -l | grep /dev/md").read().strip()
		if raidReady:
			raidPath = re.findall("\/dev\/md\d+", raidReady)[0]
			if not os.path.exists(mountPath):
				os.mkdir(mountPath)
			cmd = "sudo mount -t xfs " + raidPath + " " + mountPath;
			setStatus("mounting")
			os.popen(cmd).read().strip()
		else:
			sleep(1)