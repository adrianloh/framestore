#!/bin/sh
# chkconfig: 345 30 01
# description: framestore notification service

service_base=/tmp/service_framestore
service_file=$service_base/framestore.py
lockfile=/var/lock/subsys/framestore

BASE=https://badabing.firebaseio-demo.com
INSTANCE_ID=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
URL=$BASE/framestores/$INSTANCE_ID.json

case $1 in
	start)
		[ -d $service_base ] && rm -R $service_base
        /usr/bin/git clone https://github.com/adrianloh/framestore.git $service_base 2>/dev/null 1>/dev/null
        touch $lockfile
		nohup /usr/bin/python $service_file > /tmp/framestore.log &
		;;
	restart)
		kill -9 `ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		nohup /usr/bin/python $service_file > /tmp/framestore.log &
		;;
	status)
		proc=`ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		if [ -n "$proc" ]; then
			echo Framestore is running \($proc\)...
		else
			echo Framestore is stopped
		fi
		;;
    stop)
		proc=`ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		if [ -n "$proc" ]; then
			kill -9 $proc
			[ -d $service_base ] && rm -R $service_base
			[ -f $lockfile ] && rm -f $lockfile
			curl -sX DELETE $URL > /dev/null
			echo Framestore is stopped
		else
			echo Framestore is not running
		fi
		;;
esac