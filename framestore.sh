#!/bin/sh
# chkconfig: 345 30 01
# description: framestore notification service

name=framestore
service_base=/tmp/service_${name}
service_file=${service_base}/${name}.py
lockfile=/var/lock/subsys/${name}
pidfile=/var/run/${name}.pid
logfile=/tmp/${name}.log

initscript="https://raw.github.com/adrianloh/framestore/master/${name}.sh"
initfile=/etc/init.d/${name}
curl -s ${initscript} > ${initfile}
chmod +x ${initfile}

GITBASE="https://github.com/adrianloh/framestore.git"
INSTANCE_ID=`curl -s http://169.254.169.254/latest/meta-data/instance-id`

getProc () {
	echo `ps ax | grep ${service_file} | grep -v grep | awk '{print $1}'`;
}

launch() {
	cd ${service_base}
	version=`/usr/bin/git log --oneline | head -n1 | awk '{print $1}'`
	echo -e "\033[33mFramestore server starting... ($version)...\033[0m"
	nohup /usr/bin/python ${service_file} > ${logfile} &
	touch ${lockfile}
	sleep 5
	if [ -f ${pidfile} ]; then
		echo -e "\033[32mFramestore server is running ($proc)...\033[0m"
	else
		echo -e "\033[31mFramestore server failed to start. Check $logfile\033[0m"
	fi
}

die() {
	proc=`getProc`
	if [ -n "$proc" ]; then
		kill -9 ${proc}
        base=`/usr/bin/python ${service_base}/getbase.py`
		curl -sX DELETE ${base}/framestores/${INSTANCE_ID}.json > /dev/null
		[ -d ${service_base} ] && rm -R ${service_base}
		[ -f ${lockfile} ] && rm -f ${lockfile}
		echo Framestore is stopped
	else
		echo Framestore is not running
	fi
}

case $1 in
	start)
		proc=`getProc`
		if [ -n "$proc" ]; then
			echo -e "\033[32mFramestore server is already running ($proc)...\033[0m"
		else
			[ -d ${service_base} ] && rm -R ${service_base}
			[ -f ${pidfile} ] && rm ${pidfile}
			/usr/bin/git clone ${GITBASE} ${service_base} 2>/dev/null 1>/dev/null
			launch
		fi
		;;
	restart)
		die
		sleep 1
		launch
		;;
	status)
		proc=`getProc`
		if [ -n "$proc" ]; then
			echo -e "\033[32mFramestore server is running ($proc)...\033[0m"
		else
			echo -e "\033[31mFramestore server is stopped\033[0m"
		fi
		;;
    stop)
		`die`
		;;
esac