#! /bin/sh

name=framestore
GITBASE="https://github.com/adrianloh/framestore.git"

initscript=`echo ${GITBASE} | sed -e "s|github|raw.github|" -e "s|.git$|/master/${name}.sh|"`

if [ `id -u` -ne 0 ]
then
	echo -e "\033[31mYou must run this script as root.\033[0m"
	exit 1
fi

if [[ `service nfs status 2>&1` =~ unrecognized ]]; then
	echo -e "\033[33mInstalling NFS services\033[0m"
	yum -y install portmap nfs-utils
fi

if [[ `git 2>&1` =~ "command not found" ]]; then
	echo -e "\033[33mInstalling Git\033[0m"
	yum -y install git
fi

echo -e "\033[33mStarting NFS services\033[0m"
for serv in rpcbind nfs nfslock; do
	chkconfig ${serv} on && service ${serv} start;
done

echo -e "\033[33mInstalling Framestore server\033[0m"
initfile=/etc/init.d/${name}
curl -s ${initscript} > ${initfile}
chmod +x ${initfile}

echo -e "\033[33mSetting Framestore to run at startup\033[0m"
ln -fs ${initfile} /etc/rc3.d/S30${name}
chkconfig --add ${name}
chkconfig ${name} on

echo -e "\033[33mBooting Framestore server\033[0m"
service ${name} start