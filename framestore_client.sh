#!/bin/sh
# chkconfig: 345 30 01
# description: framestore notification service

name=framestore_client
service_base=/tmp/service_$name
service_file=$service_base/$name.py
lockfile=/var/lock/subsys/$name
logfile=/tmp/$name.log
initfile=/etc/init.d/$name

GITBASE=https://raw.github.com/adrianloh/framestore/master
curl -s $GITBASE/$name.sh > $initfile
chmod +x $initfile

case $1 in
	start)
		[ -d $service_base ] && rm -R $service_base
		/usr/bin/git clone https://github.com/adrianloh/framestore.git $service_base 2>/dev/null 1>/dev/null
		touch $lockfile
		nohup /usr/bin/python $service_file > $logfile &
        sleep 2
        proc=`ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		if [ -n "$proc" ]; then
            echo -e "\033[32mFramestore client is running ($proc)...\033[0m"
		else
            echo -e "\033[31mFramestore client failed to start. Check $logfile\033[0m"
		fi
		;;
	restart)
		kill -9 `ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		nohup /usr/bin/python $service_file > $logfile &
		;;
	status)
		proc=`ps ax | grep $service_file | grep -v grep | awk '{print $1}'`
		if [ -n "$proc" ]; then
            echo -e "\033[32mFramestore client is running ($proc)...\033[0m"
		else
            echo -e "\033[31mFramestore client is stopped\033[0m"
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
			echo Framestore client is not running
		fi
		;;
esac