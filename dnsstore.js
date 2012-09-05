var dgram = require('dgram');
var solr = require('solr');
var config = require("./config/config.js");
var amqp = require("amqp");
//var memcache = require('memcache');
//var uuid = require('simple-uuid');
var crypto = require('crypto');
var redis = require('redis');
var packs = Array();


//var redisc = redis.createClient(null, '172.16.185.8', 6379);
var redisc = redis.createClient(config.redis_port, config.redis_ip);


var client = solr.createClient(
{ host: config.solr_ip,
  port: config.solr_port,
  core: config.solr_core
});

setInterval(function() { client.commit();  }, 1000);

//var mcache = new memcache.Client(11211, 'localhost');
//mcache.port = 11211;
//mcache.host = 'localhost';

//mcache.connect();




function setup() {
    var queue = amqpcon.queue(config.amqp_work_queue);
    var queue = amqpcon.queue(config.amqp_work_queue, {durable: false, exclusive: false}, function() {
        console.log("queue");
        queue.bind(config.amqp_exchange, "#");
        queue.subscribe( {ack:true}, function(message){
            if (skip(message.packet)) { queue.shift(); return } // skip packets we don't want
            message.packet = clusterize(message.packet);
            save_to_redis(message.packet);
            save_to_solr(message.packet);
            queue.shift();
        });
    });

}


console.log("DNS indexing. connecting to AMQP: " + config.amqp_url);
var amqpcon = amqp.createConnection({url: config.amqp_url});
amqpcon.on('ready', setup);

function redis_store_update(key, value) {
    var firstseen = Date();
    var lastseen = Date();
    

    redisc.hmget(key, "count", "firstseen", function(err, d) {
        var count = parseInt(d[0], 10);
        if (err || d == "null" || d == "NaN" || d == null || isNaN(count)) {
            count = 1;

        }  else { 
            count = count + 1;
            if (d[1] != null && d[1] != "null") {
                firstseen = d[1];
            }
        }
        
        redisc.hmset(key, {"query": value, "count": count, "lastseen": lastseen, "firstseen": firstseen}, function(err, msg) {
            if (err) {
                console.log("error " + err);
                console.log(key + " => " + value);
            }
        });
    });

}

function save_to_redis(packet) {
    for (var i = 0; i < packet.query.length; i++) {
        
        key = packet.query[i] +  ":" + packet.cluster[i] + ":" + packet.rcode;
        value = JSON.stringify(packet);
        redis_store_update(key, value);
    }
    for (var j =0; j < packet.response.length; j++) {
        key = packet.response[j] + ";" + packet.query[j];
        value = JSON.stringify(packet);
        redis_store_update(key, value);
    }

}


function save_to_solr(packet) {
    packs.push(packet);
    if (packs.length > config.buffer) {
        var npacks = packs;
        packs = Array();
        client.add(packet, function(err) {
            if (err) {
                console.log(err);
            }
        });
    }
    
    / *console.log(JSON.stringify(rawMessage)); */

}

function skip(packet) {
    var ignore = [
    /relays.visi.com$/i,
    /dnsbl.void.ru$/i,
    /spamhaus/i,
    /userapi.com$/i,
    /dsbl.org/i,
    ]
 for (var i = 0; i< packet.query.length; i++) {
     // we don't want to keep track of in-addr.arpa stuff
     for (var j = 0; j < ignore.length; j++) {
         if (packet.query[i].match(ignore[j])) {
             return true;
         }
     }
     // some standard ignores
     if (packet.query[i].match(/in-addr.arpa/i)) {
         return true;
     }
     if (packet.query[i].match(/.ip6.arpa/i)) {
         return true;
     }
     if (packet.query[i].match(/local/i)) {
         return true;
     }
     if (packet.query[i].match(/spamcop.net/i)) {
         return true;
     }
     if (packet.query[i].match(/rarus.ru$/i)) {
         return true;
     }
     if (packet.query[i].match(/loc$/i)) {
         return true;
     }
     if (packet.query[i].match(/Dlink$/i)) {
         return true;
     }
     if (packet.query[i].match(/yotaaccessinterface/i)) {
         return true;
     }
     if (packet.query[i] == 'localhost') {
         return true;
     }
 }
 return false;
}


function clusterize(packet) {

    packet.cluster = Array();
    for (var i = 0; i< packet.query.length; i++) {
        var doms = packet.query[i].split('.');
        if (doms.length < 2) {
            packet.cluster.push(packet.query[i].length);
        } else {
            var c = doms[doms.length - 1 ] + "_" + doms[doms.length -2].length.toString() + "_" + packet.query[i].length.toString(); // similarity distance
            packet.cluster.push(c);
        }
    }
    return packet;
}


process.on('uncaughtException', function(err) {
    console.log("Uncaught Exception " + err);
});
