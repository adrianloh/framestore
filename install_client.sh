#! /bin/sh

yum -y install portmap nfs-utils git

service rpcbind start
service nfs start
service nfslock start

chkconfig nfs on
chkconfig nfslock on
chkconfig rpcbind on

initfile=/etc/init.d/framestore_client
curl -s https://raw.github.com/adrianloh/framestore/master/framestore_client.sh > $initfile
chmod +x $initfile
ln -fs $initfile /etc/rc3.d/S30framestore_client
chkconfig -add framestore_client
chkconfig framestore_client on
service framestore_client start