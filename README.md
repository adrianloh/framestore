# FRAMESTORE
======

Share filesystems across EC2 instances. Any machine in a cluster can
both be a server and a client. Framestore looks for RAID arrays that
are comprised of EBS volumes.

For a 2-node example, first create two EC2 instances.

##### Important: pass in to the machines under user-data:

![alt text](http://farm6.staticflickr.com/5491/11188153184_43ff050685_c.jpg "Set user-data")

Base identifies machines as belonging to a cluster, and is simply the
prefix of a Firebase location e.g. `https://clustername.firebaseio.com`
You can go here to see the details of the fileshares.

Now imagine we have two instances with ids: **i-c0702596** and **i-1bc5ef4d**.

First, create a RAID system comprised of 20 5GB drives and attach it
to **i-c0702596** (the fileserver):

```
ec2-create-cluster-fs merovingian 20x5 i-c0702596 /path/to/file.pem
```

Now inside **i-c0702596**, as root:

```
wget "https://raw.github.com/adrianloh/framestore/master/install.sh"
sh install.sh framestore
```

After installation, Framestore will look for mounted raids and publish
them for clients to find.

The name of the cluster filesystem (e.g. merovingian) is by default
where *all* the machines in the cluster will mount the share: `/media/merovingian`

Now inside **i-1bc5ef4d** (the client), as root:

```
wget "https://raw.github.com/adrianloh/framestore/master/install.sh"
sh install.sh framestore-client
```

Now, if you wanna monitor the output of the service:

```
tail -f /tmp/framestore.log
```