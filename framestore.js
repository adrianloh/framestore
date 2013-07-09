var Firebase = require("firebase"),
	MaggieBase = new Firebase("https://badabing.firebaseio-demo.com/"),
	FramestoresBase = MaggieBase.child('framestores'),
	machineIsLive = MaggieBase.child(".info").child("connected"),
	exec = require('child_process').exec,
	fs = require("fs"),
	async = require("async"),
	machineBase;

exec("curl -s http://169.254.169.254/latest/meta-data/instance-id",
	function(error, stdout, stderr) {
		var hostname;
		if (stdout && stdout.match(/^i-/)) {
			hostname = stdout;
		} else {
			hostname = process.env.HOSTNAME;
		}
		machineBase = FramestoresBase.child(hostname);
		machineBase.set("Waiting for filesystem...");
		machineBase.onDisconnect().remove();
	});

var mounting = false,
	checkForMounted = setInterval(function() {
	if (mounting) { return; }
	exec('sudo fdisk -l | grep /dev/md',
		function (error, stdout, stderr) {
			if (stdout.length>0) {
				mounting = true;
				var dev = "/dev/" + stdout.match(/(md\d+):/)[1],
					target = "/media/framestore";
				async.series([
					function checkSanityOfPaths(stepDone) {
						if (dev.match(/\/dev\/md\d+/)) {
							stepDone();
						} else {
							stepDone("Wonky device path: " + dev);
						}
					},
					function checkMountPoint(stepDone) {
						fs.exists(target, function (exists) {
							if (!exists) {
								fs.mkdirSync(target);
							}
							stepDone();
						});
					},
					function mountFilesystem(stepDone) {
						var cmd = "mount | grep " + target;
						exec(cmd, function(error, stdout, stderr) {
							if (stdout.length===0) {
								cmd = "sudo mount -t xfs " + dev + " " + target;
								console.log(cmd);
								exec(cmd, function(error, stdout, stderr) {
									stepDone(error);
								});
							} else {
								stepDone("A filesystem is already mounted at " + target + " " + stdout);
							}
						});
					}
				], function onComplete(error) {
					if (!error) {
						clearInterval(checkForMounted);
						exec("df -h | grep md", function(error, stdout, stderr) {
							if (stdout.length>0) {
								var s = {},
									stat = stdout.split(" ").filter(function(o) { return o.length>0 });
								s.available = stat[1];
								s.used = stat[2];
								s.free = stat[3];
								s.device = stat[0];
								s.mount = stat[5];
								machineBase.set(s);
							}
						});
					} else {
						console.log(error);
						if (typeof(error)==='string' && error.match(/already mounted/)) {
							clearInterval(checkForMounted);
						} else {
							mounting = false;
						}
					}
				});
			}
		});
}, 2500);