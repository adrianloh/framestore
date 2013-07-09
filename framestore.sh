#!/bin/sh
# chkconfig: 345 30 01
# description: framestore notification service

service_base=/tmp/service_framestore
service_file=$service_base/framestore.py

case $1 in
	start)
		[ -d $service_base ] && rm -R $service_base
        /usr/bin/git clone https://github.com/adrianloh/framestore.git $service_base
		/usr/bin/python $service_file &
		;;
	restart)
		kill -9 `ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		/usr/bin/python $service_file
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
		echo Framestore is stopped
		;;
esac