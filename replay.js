var walk    = require('walk');
var dgram = require('dgram');
var fs = require('fs');
var files   = [];

var client = dgram.createSocket('udp4');


// Walker options
var walker  = walk.walk('/home/fygrave/devel/ph/tmp/packs', { followLinks: false });

walker.on('file', function(root, stat, next) {
    // Add this file to the list of files
    //files.push(root + '/' + stat.name);
    fs.readFile(root + '/' + stat.name, function (err, data) {
	if (! err) {
	  //  console.log(data);
	    client.send(data, 0, data.length, 325, "localhost");
	}
    });
    next();
});

walker.on('end', function() {
    console.log(files);
});
