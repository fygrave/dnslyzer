var dgram = require('dgram');
var solr = require('node-solr');
//var memcache = require('memcache');
//var uuid = require('simple-uuid');
var crypto = require('crypto');



var client = solr.createClient(
{ host: 'localhost',
  port: 8983,
//  core: '/core01'
});


//var mcache = new memcache.Client(11211, 'localhost');
//mcache.port = 11211;
//mcache.host = 'localhost';

//mcache.connect();





sock = dgram.createSocket('udp4');

sock.on('message', function(rawMessage, rinfo) {
    if (rawMessage[2] == 81 && rawMessage[3] == 83) {
	console.log("response -> no name found");
    }
   
    var packet = {};
    packet.id = rawMessage[12] * 256 + rawMessage[13];
    packet.type = rawMessage[14] * 256 + rawMessage[15];
    packet.qr = (packet.type& 0x8000)>>15;
    packet.opcode = (packet.type & 0x7000) >> 14;
    packet.aa = (packet.type &0x800) >>  11;
    packet.tc = (packet.type & 0x400) >> 10;
    packet.rd = (packet.type & 0x200) >> 9;
    packet.ra = (packet.type & 0x100) >> 8;
    packet.rcode = (packet.type & 0x7);
    console.log("qr:" + packet.qr + " opcode:" + packet.opcode + " aa:" + packet.aa + " rcode: " + packet.rcode);
    packet.qdcount = rawMessage[16] * 256 + rawMessage[17];
    packet.ancount = rawMessage[18] * 256 + rawMessage[19];
    packet.nscount = rawMessage[20]*256 + rawMessage[21];
    packet.arcount = rawMessage[22] * 256 + rawMessage[23];
    console.log("q:" + packet.qdcount + " an:" + packet.ancount + " ns:" + packet.nscount + " ar:" + packet.arcount);
    //parse question
    packet.query = Array();
    packet.response = Array();
    packet.response_ttl = Array();
    var offset = 24; // starting offset for DNS packet body
    for (var i = 0; i< packet.qdcount; i++) {
	
	var s;
	var rez = getDomain(rawMessage, offset);
	s = rez[0];
	offset = rez[1] + 4; // 4 octets QTYPE and QCLASS
	packet.query.push(s);
	console.log("s: " + s + " all: " + getAllChars(rawMessage));
    }
    offset = offset + 1; // trailing 0
    //console.log("answer len: " + rawMessage[offset].toString(16));
    for (var i=0; i< packet.ancount; i++) {
	if (rawMessage[offset] == 0xc0) { // name is pointer skip
            var ttl = rawMessage[offset+7] * 16777216  + rawMessage[offset+ 8 ] * 65536+ rawMessage[offset + 9] * 256 + rawMessage[offset + 10];
	    offset = offset + 10; // skip pointer (2), answer type (2), answer class(2) and ttl (4)

    //console.log(packet.id.toString(16) + " : " + packet.type.toString(16));
    //parse answer
    	
	var rdlen = rawMessage[offset] * 256 + rawMessage[offset +1];
	//console.log("rdlen: " + rdlen);
	var rdata = rawMessage[offset + 5] + "." + rawMessage[offset + 4] + "." + rawMessage[offset + 3] + "." + rawMessage[offset + 2];
	    packet.response.push(rdata);
            packet.response_ttl.push(ttl);
	console.log("rdata: " + rdata);
	offset = offset + rdlen;
	}
    }
    // we ignore ns section for now
    var hash = crypto.createHash('sha1');
    hash.update(rawMessage);
    hash.update(process.pid.toString());
    hash.update(new Date().toString());

    
    packet.id = hash.digest("hex"),

    console.log(JSON.stringify(packet));
    client.add(packet, function(err) {
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

function getDomain(buf, offset) {
    var r_off = offset;
    var r_dom = ''
    var num = buf[offset];
    r_dom = getChars(buf, offset);
    r_off = offset + num + 1;
    while (buf[r_off] != 0) {
	r_dom = r_dom + "." + getChars(buf, r_off);
	
	r_off = r_off + buf[r_off] + 1;
    }
    return [r_dom, r_off];

}

function getChars(buf, offset) {
    var num = buf[offset];
    var ret = '';
    for (var i = offset + 1; i < offset + num + 1; i++) {
	if (buf[i] > 32 && buf[i] < 128) {
            ret = ret + String.fromCharCode(buf[i]);
	} else {
            ret = ret + '.';
	} 
    }
    return ret;
}
function getAllChars(buf) {
    var ret = '';
    for (var i = 0; i < buf.length; i++) {
	if (buf[i] > 32 && buf[i] < 128) {
            ret = ret + String.fromCharCode(buf[i]);
	} else {
            ret = ret + " " +  buf[i].toString(16) + " " ;
	}
    }
    return ret;
}

sock.bind(325);


//process.on('uncaughtException', function(err) {
//    console.log("Uncaught Exception " + err);
//});
