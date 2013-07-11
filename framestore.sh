#!/bin/sh
# chkconfig: 345 30 01
# description: framestore notification service

name=framestore
service_base=/tmp/service_${name}
service_file=${service_base}/${name}.py
lockfile=/var/lock/subsys/${name}
pidfile=/var/run/${name}.pid
logfile=/tmp/${name}.log

GITBASE="https://github.com/adrianloh/framestore.git"
INSTANCE_ID=`curl -s http://169.254.169.254/latest/meta-data/instance-id`
DEFAULT_BASE="https://badabing.firebaseio-demo.com"

initfile=/etc/init.d/${name}

initscript=`echo ${GITBASE} | sed -e "s|github|raw.github|" -e "s|.git$|/master/framestore.sh|"`
if [[ name =~ "client" ]]; then
	curl -s ${initscript} | sed -e 's|name=framestore|name=framestore-client|' > ${initfile}
else
	curl -s ${initscript} > ${initfile}
fi

chmod +x ${initfile}

getProc () {
	echo `ps ax | grep ${service_file} | grep -v grep | awk '{print $1}'`;
}

launch() {
	cd ${service_base}
	version=`/usr/bin/git log --oneline | head -n1 | awk '{print $1}'`
	echo -e "\033[33m${name} starting ($version)...\033[0m"
	nohup /usr/bin/python ${service_file} > ${logfile} &
	touch ${lockfile}
	sleep 5
	if [ -f ${pidfile} ]; then
		proc=`cat ${pidfile}`
		echo -e "\033[32m${name} is running ($proc)...\033[0m"
	else
		echo -e "\033[31m${name} failed to start. Check $logfile\033[0m"
	fi
}

die() {
	proc=`getProc`
	if [ -n "$proc" ]; then
		kill -9 ${proc}
		res=`curl -s http://169.254.169.254/latest/user-data | grep base=`
		if [ -n "${res}" ]; then
			base=`echo ${res} | cut -d= -f2`
		else
			base=${DEFAULT_BASE}
		fi
		url="${base}/framestores/${INSTANCE_ID}.json"
		echo -e "[ \033[31mSTOP\033[0m ] broadcast: ${url}"
		curl -sX DELETE ${url} > /dev/null
		[ -d ${service_base} ] && rm -R ${service_base}
		[ -f ${lockfile} ] && rm -f ${lockfile}
		echo "${name} is stopped"
	else
		echo "${name} is not running"
	fi
}

case $1 in
	start)
		proc=`getProc`
		if [ -n "$proc" ]; then
			echo -e "\033[32m${name} is already running ($proc)...\033[0m"
		else
			[ -d ${service_base} ] && rm -R ${service_base}
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
			echo -e "\033[32m${name} is running ($proc)...\033[0m"
		else
			echo -e "\033[31m${name} is stopped\033[0m"
		fi
		;;
    stop)
		die
		;;
esac