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

base = "badaboom"

cmd = "curl -s -m 2 %s | grep base=" % amazon['user-data']
userbase = os.popen(cmd).read().strip()
if userbase:
	base = userbase.split("=")[1]
else:
	log("WARNING: Using default Firebase: " + base)

base = "https://%s.firebaseio-demo.com" % base
framestoreBase = base + '/framestores'
machineBase = framestoreBase + '/' + instance_id
stat = {
	'public_ip': public_ip,
	'private_ip': private_ip,
	'hostname': hostname,
	'zone': zone
}

filesystems_status = {}

cmd = """curl -sX PUT -d '%s' %s""" % (json.dumps(stat), machineBase + ".json")
res = os.popen(cmd).read()
if res and not re.match("error", res):
	log("Server " + hostname + " is up @ " + private_ip + ". Broadcasting presence to " + base)
else:
	log("FATAL: Failed broadcast to Firebase: " + base)
	exit(1)

pidfile = "/var/run/framestore.pid"
os.popen("echo %i > %s" % (os.getpid(), pidfile)).read()

@atexit.register
def removeBase():
	log("Framestore server shutdown.")
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


def setShareStatus(shareName, status):
	key = "filesystems/" + shareName + "/status"
	setData(key, status)


def getClusterName(devicePath):
	"""
	Given a path like /dev/xvdg to a device that belongs in a cluster group,
	figure out the name of the cluster.
	The very arcane "mappings" line turns the BLOCKDEVICE section of ec2-describe-instances:
	BLOCKDEVICE	/dev/xvda	vol-d9aaf49a	2013-12-02T13:02:31.000Z	true
	BLOCKDEVICE	/dev/xvdh	vol-edeab4ae	2013-12-02T15:28:32.000Z	false
	BLOCKDEVICE	/dev/xvdf	vol-05eab446	2013-12-02T15:28:32.000Z	false
	BLOCKDEVICE	/dev/xvdi	vol-eceab4af	2013-12-02T15:28:32.000Z	false
	into a dictionary like this:
		{'/dev/xvda': 'vol-d9aaf49a',
		'/dev/xvdf': 'vol-05eab446',
		'/dev/xvdh': 'vol-edeab4ae',
		'/dev/xvdi': 'vol-eceab4af'}
	"""
	clusterName = None
	zoner = re.search("us-east", zone) and "ec2.us-east-1.amazonaws.com" or "ec2.ap-southeast-1.amazonaws.com"
	prefix = """export EC2_URL=ZONE; MY_COMMAND --aws-access-key AKIAJEJZXTMENIS4GJVQ --aws-secret-key 0CdRkLj9UOIPTbN9yboNOmfeom2QrK8Kc+pMcH51 """
	prefix = re.sub("ZONE", zoner, prefix)
	cmd1 = prefix +  " INSTANCE_ID | grep BLOCKDEVICE""".replace("INSTANCE_ID", instance_id)
	ec2_describe_instances = re.sub("MY_COMMAND", "ec2-describe-instances", cmd1)
	mappings = dict([(ll[1],ll[2]) for ll in [l.split("\t") for l in os.popen(ec2_describe_instances).read().split("\n") if l]])
	if devicePath in mappings.keys():
		volumeId = mappings[devicePath]
		cmd2 = prefix + " VOLUME_ID | grep TAG | awk '{print $5}'".replace("VOLUME_ID", volumeId)
		ec2_describe_volume = re.sub("MY_COMMAND", "ec2-describe-volumes", cmd2)
		clusterName = os.popen(ec2_describe_volume).read().strip()
	return clusterName


def mdadmName(dev):
	cmd = "mdadm --detail %s | grep Name" % dev
	raidName = os.popen(cmd).read().strip()
	if len(raidName.split(":")) > 1:
		raidName = raidName.split(":")[-1].strip().split(" ")[0]
	else:
		return getClusterName(dev)
	if re.match("^\d+$", raidName) or len(raidName) == 0:
		return None
	else:
		return raidName


def exportNfs(mountPath):
	global filesystems_status
	raidName = os.path.split(mountPath)[-1]
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
		filesystems_status[raidName] = "online"
	else:
		filesystems_status[raidName] = "ready"
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
	raidsReady = [l.strip() for l in os.popen("fdisk -l | grep /dev/md").readlines() if l]
	keys = ['device', "capacity", "usedSpace", "free", "usedPercent", "mount"]
	exports = dict(filesystems={})
	filesystems = exports['filesystems']
	for fdiskDetail in raidsReady:
		raidPath = re.findall("/dev/md\d+", fdiskDetail)[0]
		mdPath = os.path.split(raidPath)[-1]
		raidName = mdadmName(raidPath)
		if raidName:
			mountPath = "/media/" + raidName
			isMounted = os.popen("mount | grep " + mountPath).read().strip()
			log("RAID present: " + raidPath)
			if isMounted:
				touchDir = mountPath + "/.connected/"
				try:
					if not os.path.exists(touchDir):
						os.mkdir(touchDir)
					log("RAID mounted: " + mountPath)

					# Another way of finding established connections to this machine:
					# netstat -vat | grep nfs.*ESTABLISHED

					# Each connected client will periodically touch a file whose name
					# is its own instance_id inside the server's .connected folder
					# This is how we establish that the client is still around.
					connected = [f for f in os.listdir(touchDir) if os.path.isfile(touchDir + f) and time() - os.path.getmtime(touchDir + f) < 60]

					# Get the drive stats for this RAID. df -h 's output looks like:
					# Filesystem            Size  Used Avail Use% Mounted on
					# /dev/xvda1            7.9G  2.9G  5.0G  37% /
					# tmpfs                 298M     0  298M   0% /dev/shm
					# /dev/md127            5.0G   33M  5.0G   1% /media/milano
					res = os.popen("df -h | grep %s" % mdPath).read().strip()
					if res:
						data = res.split()
						publish = filesystems[raidName] = dict(zip(keys, data))
						publish['status'] = filesystems_status.has_key(raidName) and filesystems_status[raidName] or "offline"
						publish['clients'] = len(connected)
						publish['files'] = countFile(mountPath)
						patchData(exports)
					exportNfs(mountPath)
				except OSError as e:
					log("ERROR Exception: " + str(e))
					setShareStatus(raidName, "error")
			else:
				log("Mounting RAID " + raidPath + " to " + mountPath)
				try:
					if not os.path.exists(mountPath):
						os.mkdir(mountPath)
					cmd = "mount " + raidPath + " " + mountPath
					setShareStatus(raidName, "mounting")
					os.popen(cmd).read().strip()
				except Exception as e:
					log("ERROR Exception: " + str(e))
					setShareStatus(raidName, "error")

	touch(pidfile)
	sleep(5)