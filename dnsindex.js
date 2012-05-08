var dgram = require('dgram');
var solr = require('node-solr');
var memcache = require('memcache');
var uuid = require('simple-uuid');

var client = solr.createClient(
{ host: '172.16.185.8',
  port: 8983,
  core: '/core01'
});


var mcache = new memcache.Client(11211, 'localhost');
mcache.port = 11211;
mcache.host = 'localhost';

mcache.connect();





sock = dgram.createSocket('udp4');

sock.on('message', function(rawMessage, rinfo) {
    if (rawMessage[2] == 81 && rawMessage[3] == 83) {
	console.log("response -> no name found");
    }
   
    var packet = {};
    packet.id = rawMessage[12] * 256 + rawMessage[13];
    packet.type = rawMessage[14] * 256 + rawMessage[15];
    packet.questions = rawMessage[16] * 256 + rawMessage[17];

    //console.log(packet.id.toString(16) + " : " + packet.type.toString(16));
    r = '';
    for (i = 0; i < rawMessage.length; i++) {
	if (rawMessage[i] > 32 && rawMessage[i] < 128) {
            r = r + String.fromCharCode(rawMessage[i]);
	} else {
            r = r + '.';
	}
    }
    var doc = {
        id: uuid(),
	query: packet.type,
        rawstring: r
    };
    client.add(doc, function(err) {
	if (err) {
	    console.log(err);
	}
    });
    client.commit();
    
    / *console.log(JSON.stringify(rawMessage)); */

});

sock.on('listening', function() {
    var address = sock.address();
    console.log("server on " + address.address + " port " + address.port);

});


sock.bind(325);
