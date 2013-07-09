#!/bin/sh
# chkconfig: 345 30 01
# description: framestore notification service
#
# curl -s https://renegade-princess.s3-ap-southeast-1.amazonaws.com/framestore.sh > /etc/init.d/framestore
# chmod +x /etc/init.d/framestore

service_base=/tmp/service_framestore_client
service_file=$service_base/framestore_client.py
lockfile=/var/lock/subsys/framestore_client
logfile=/tmp/framestore_client.log

BASE=https://badabing.firebaseio-demo.com

case $1 in
	start)
		[ -d $service_base ] && rm -R $service_base
		/usr/bin/git clone https://github.com/adrianloh/framestore.git $service_base 2>/dev/null 1>/dev/null
		touch $lockfile
		nohup /usr/bin/python $service_file > $logfile &
		;;
	restart)
		kill -9 `ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		nohup /usr/bin/python $service_file > $logfile &
		;;
	status)
		proc=`ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		if [ -n "$proc" ]; then
			echo Framestore client is listening \($proc\)...
		else
			echo Framestore client is stopped
		fi
		;;
    stop)
		proc=`ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		if [ -n "$proc" ]; then
			kill -9 $proc
			[ -d $service_base ] && rm -R $service_base
			[ -f $lockfile ] && rm -f $lockfile
			echo Framestore client is stopped
		else
			echo Framestore client is already stopped
		fi
		;;
esac