#!/bin/sh
# chkconfig: 345 30 01
# description: framestore notification service
#
# curl -s https://renegade-princess.s3-ap-southeast-1.amazonaws.com/framestore.sh > /etc/init.d/framestore
# chmod +x /etc/init.d/framestore

service_base=/tmp/service_framestore
service_file=$service_base/framestore.py
lockfile=/var/lock/subsys/framestore
alias exec="/usr/bin/python"

case $1 in
	start)
		[ -d $service_base ] && rm -R $service_base
        /usr/bin/git clone https://github.com/adrianloh/framestore.git $service_base
        touch $lockfile
		exec $service_file &
		;;
	restart)
		kill -9 `ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		exec $service_file
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
		kill -9 `ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		rm -R $service_base
		rm -f $lockfile
		echo Framestore is stopped
		;;
esac