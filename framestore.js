var Firebase = require("firebase"),
	MaggieBase = new Firebase("https://badabing.firebaseio-demo.com/"),
	FramestoresBase = MaggieBase.child('framestores'),
	machineIsLive = MaggieBase.child(".info").child("connected"),
	exec = require('child_process').exec,
	fs = require("fs"),
	async = require("async");

var machineBase = FramestoresBase.child(process.env.INSTANCE_ID);

machineBase.onDisconnect().remove();

var checkForMounted = setInterval(function() {
	exec('sudo fdisk -l | grep /dev/md',
		function (error, stdout, stderr) {
			if (stdout.length>0) {
				var dev = "/dev/" + stdout.match(/(md\d+):/)[1],
					target = "/media/framestore";
				async.series([
					function(stepDone) {
						fs.exists(target, function (exists) {
							if (!exists) {
								fs.mkdirSync(target);
							}
							stepDone();
						});
					},
					function(stepDone) {
						if (fs.readdirSync(target).length===0) {
							exec("sudo mount -t xfs " + dev + " " + target, function(error, stdout, stderr) {
								stepDone(error);
							});
						} else {
							stepDone();
						}
					}
				], function onComplete(error) {
					if (!error) {
						clearTimeout(checkForMounted);
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
					}
				});
			}
		});
}, 10000);