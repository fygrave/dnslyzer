
// take parsed DNS packets. Maintain clusters. sync clusters into reddis
// identify 'botnet' and 'malware' related clusters
var amqp = require("amqp");
var redis = require('redis');
var config = require("./config/config.js");
var active_clusters =Array ();



var redisc = redis.createClient(config.redis_port, config.redis_ip);


function setup() {
    var queue = amqpcon.queue("cluster_queue", {durable: false, exclusive: false}, function() {
        console.log("queue");
        queue.bind(config.amqp_exchange,'');
        queue.subscribe( {ack:true}, function(message){
            if (skip(message.packet)) { queue.shift(); return;}
            message.packet = clusterize(message.packet);
            save_to_redis(message.packet);
            queue.shift();
        });
    });

}


console.log("DNS indexing. connecting to AMQP: " + config.amqp_url);
var amqpcon = amqp.createConnection({url: config.amqp_url});
amqpcon.on('ready', setup);


function clusterize(packet) {

console.log(packet.query);

}

function save_to_redis(packet) {

return
}
function skip(packet) {
    console.log(packet.query);
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


