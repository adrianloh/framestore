#! /bin/bash
# NOTE: Requires Bash > v4.0 because we use dictionaries
# This is a "rescue beacon" script. In the event when the instance running this script is shutdown,
# it publishes a list of mounted RAID filesystems (if any) to IronMQ so that a successor instance
# is able to remount that filesystem upon boot.

IRONPROJECT="https://mq-aws-us-east-1.iron.io/1/projects/51bcd4dbed3d764af2000e8a"
DEFAULT_BASE="badaboom"

source "/home/ec2-user/.bash_profile"

instance=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
region=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document| grep region | awk -F\" '{print $4}'`
zone=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document| grep Zone | awk -F\" '{print $4}'`
type=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | grep instanceType | awk -F\" '{print $4}'`

# The data string that we will be publishing to IronMQ.
# In actual fact, a dictionary whose keys are prefixed with "@" e.g.
# "@key value"
publish="@region ${region}"
publish+="@zone ${zone}"

# Declare a dictionary that maps a device path -> volumeID of the EBS hosting that device
declare -A mounted
mappings=$(ec2-describe-instances --region ${region} `curl -sL bit.ly/waikeong` ${instance} | grep BLOCKDEVICE | grep false | awk '{print $2"\""$3}')
for map in ${mappings}; do
	device=`echo ${map} | awk -F\" '{print $1}'`
	volume=`echo ${map} | awk -F\" '{print $2}'`
	mounted[${device}]=${volume}
done

# Get all running and mounted RAIDs
raids=`sudo fdisk -l | grep /dev/md | tr ':' ' ' | awk '{print $2}'`

for raid in ${raids}; do
	# Get a list of device paths that make up the RAID in question...
	devices=`mdadm --detail ${raid} | grep /dev/[^m] | awk '{print $NF}'`
	# Use the first device (consequently, the first volumeID, to figure out a few things...
	first_device=`echo ${devices} | awk '{print $1}'`
	# Get the volumeID of the EBS that hosts this device from
	# the "mounted" dictionary we built earlier...
	first_volume=${mounted[${first_device}]}
	if [ -n "${first_volume}" ]; then
		# Does this device belong to a "volume cluster" e.g. Is it tagged
		# with the dictionary { "volgroup":"volume_cluster_name" }
		volgroup=$(ec2-describe-volumes --region ${region} `curl -sL bit.ly/waikeong` ${first_volume} | grep volgroup | awk '{print $5}')
		if [ -n "${volgroup}" ]; then
			# If the device is part of a named volume cluster, publish it
			publish+="@volgroup ${volgroup}"
		fi
		# For the sake of completeness and redundancy, publish also
		# the list of volumes that make up the RAID.
		for dev in ${devices}; do
			vol=${mounted[${dev}]}
			if [ -n ${vol} ]; then
				publish+="@volume ${vol}"
			fi
		done
	fi
done

DEFAULT_BASE="badaboom"
res=`curl -s http://169.254.169.254/latest/user-data | grep base=`
if [ -n "${res}" ]; then
	studio=`echo ${res} | cut -d= -f2`
else
	studio=${DEFAULT_BASE}
fi

ironqueue="${IRONPROJECT}/queues/${studio}/messages"
data="{\"messages\":[{\"body\":\"$publish\"}]}"
echo "curl -sXPOST -H \"Authorization: OAuth E9PHJUc_nzkRpVSlrvMZM0TQn3A\" -H \"Content-Type: application/json\" -d '${data}' ${ironqueue}" | bash