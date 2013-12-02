#!/bin/bash
# NOTE: Requires Bash > v4.0 because we use dictionaries
# This script checks IronMQ for "orphaned" filesystems that were detached
# when their host ec2 instance went down, and attempts to mount those filesystems.

IRONPROJECT="https://mq-aws-us-east-1.iron.io/1/projects/51bcd4dbed3d764af2000e8a"
DEFAULT_BASE="badaboom"

source "/home/ec2-user/.bash_profile"

instance=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
region=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document| grep region | awk -F\" '{print $4}'`
zone=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document| grep Zone | awk -F\" '{print $4}'`

res=`curl -s http://169.254.169.254/latest/user-data | grep base=`
if [ -n "${res}" ]; then
	studio=`echo ${res} | cut -d= -f2`
else
	studio=${DEFAULT_BASE}
fi

ironqueue="${IRONPROJECT}/queues/${studio}/messages"

getMsg() {
	# Pop a message from the IronMQ queue. You can pass in an optional timeout (in seconds).
	# Returns a string like: "messageId:::body_of_message"
	if [ -n "$1" ]; then
		url="${ironqueue}?timeout=$1"
	else
		url="${ironqueue}"
	fi
	echo `curl -sXGET -H "Authorization: OAuth E9PHJUc_nzkRpVSlrvMZM0TQn3A" ${url} | sed 's|{"messages":\[{"id":"\(.*\)","body":"\(.*\)","timeout".*$|\1:::\2|'`
}

deleteMsg() {
	# Delete a message from the IronMQ queue, passing in the messageID to delete
	curl -sXDELETE -H "Authorization: OAuth E9PHJUc_nzkRpVSlrvMZM0TQn3A" "${ironqueue}/$1"
}

cmd="ec2-attach-volume-cluster"
wget "https://renegade-princess.s3-ap-southeast-1.amazonaws.com/${cmd}"

# Declare a dictionary. Blacklisted messageIds will be stored in the keys.
declare -A blacklist

while true; do
	res=`getMsg`
	if [ -n "${res}" ]; then
		message_id=`echo ${res} | awk -F":::" '{print $1}'`
		body=`echo ${res} | awk -F":::" '{print $2}'`
		target_region=`echo ${body} | tr '@' '\n' | grep region | awk '{print $2}'`
		target_zone=`echo ${body} | tr '@' '\n' | grep zone | awk '{print $2}'`
		volume_group=`echo ${body} | tr '@' '\n' | grep volgroup | awk '{print $2}'`
		volumes=`echo ${body} | tr '@' '\n' | grep volume | awk '{print $2}'`
		if [ -z "${blacklist[$message_id]}" ]; then
			# Are we in the same region and availability zone as the deceased machine (we assume that
			# the volumes are in the same zone).
			if [ ${region} == ${target_region} -a ${zone} == ${target_zone} ]; then
				if [ -n "${volume_group}" ]; then
					# Is this a named volume cluster?
					error=`python $PWD/${cmd} ${volume_group} | grep FATAL`
					if [ -z "${error}" ]; then
						deleteMsg ${message_id}
					fi
				else
					# TODO: Run ec2-attach-volume-cluster with list of volumeIds
					echo ${volumes}
				fi
			else
				$blacklist[$message_id]=1
			fi
		fi
	fi
	sleep 60
done