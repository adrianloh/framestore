#! /bin/sh

yum -y install portmap nfs-utils git

service rpcbind start
service nfs start
service nfslock start

chkconfig nfs on
chkconfig nfslock on
chkconfig rpcbind on

echo /media/framestore  *(rw,async,no_root_squash) > /etc/exports
exportfs -ar
exportfs -v

initfile=/etc/init.d/framestore
curl -s https://raw.github.com/adrianloh/framestore/master/framestore.sh > $initfile
chmod +x $initfile
ln -fs $initfile /etc/rc3.d/S30framestore
chkconfig --add framestore
chkconfig framestore on
service framestore start