#! /bin/sh

if [ `id -u` -ne 0 ]
then
    echo -e "\033[31mYou must run this script as root.\033[0m"
    exit 1
fi

if [[ `service nfs status 2>&1` =~ unrecognized ]]; then
    echo -e "\033[33mInstalling NFS services\033[0m"
	yum -y install portmap nfs-utils git
fi

if [[ `git 2>&1` =~ "command not found" ]]; then
    echo -e "\033[33mInstalling Git\033[0m"
	yum -y install git
fi

echo -e "\033[33mStarting NFS services\033[0m"
chkconfig nfs on
chkconfig nfslock on
chkconfig rpcbind on
service rpcbind start
service nfs start
service nfslock start

echo -e "\033[33mInstalling Framestore server\033[0m"
initfile=/etc/init.d/framestore
curl -s https://raw.github.com/adrianloh/framestore/master/framestore.sh > $initfile
chmod +x $initfile

echo -e "\033[33mSetting Framestore to run at startup\033[0m"
ln -fs $initfile /etc/rc3.d/S30framestore
chkconfig --add framestore
chkconfig framestore on

echo -e "\033[33mBooting Framestore server\033[0m"
service framestore start



