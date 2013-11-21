dnslyzer
========

DNS traffic indexer and analyzer


This framework to store, index and analyse DNS records forwarded by DNS forwarder:
http://www.enyo.de/fw/software/dnslogger/

This code is part of passive DNS research project.

The code implemented as a set of prototypes in nodejs, python, and  python + voltdb

The current 'stable' version is the python version in 'distributed' folder. Volt folder contains current dev tree
where we switched from redis/elasticsearch to voltdb as the main data store. Nodejs contains the first version of the code and might be of 
a historical interest.

DNS logger is a patched version of dnslogger.

Running Passive DNS and DNS analyzer
===================================
You need RabbitMQ, redis, ElasticSearch installed on the machine.

if you don't want data in redis. don't run redis worker
if you don't want data in elasticsearch, don't run redis collector.

run dns-traffic sniffers on your agents as:

create configuration file. dnscollect.cfg
```
 [main]
 dnsport = 325
 [amqp]
 host = 1.2.3.4
 port = 5672
 packetex = dnspacket
```
this is config file for supervisord to run pdns components:
```
[program:dnsredis]
directory = /pdns/redis-conf
command = redis-server redis.conf
autostart = true
autorestart = true

[program:dnscollector]
directory = /pdns/dnslyzer/distributed
command = ./dnscollsrv.py dnscollect.cfg
autostart = true
autorestart = true



[program:redisworker01]
directory = /pdns/dnslyzer/distributed
command = python redisworker.py
autorestart = true
autostart = true


[program:redisworker02]
directory = /pdns/dnslyzer/distributed
command = python redisworker.py
autorestart = true
autostart = true



[program:esworker]
directory = /pdns/dnslyzer/distributed
command = python esworker.py
autorestart = true
autostart = true
```
Data format in Redis
====================

- all clusters are stored as $clusterid$rcode sets (domain)
- all domains are stored as @domain sets (  <type>:data:rcode)
- all data is stored as &data sets (domain)
- counts stored as domain:data -> count
- first seen timestamp is stored  as dom;res;rcode -> timestamp ( * 86400)
- last seen timestamp is stored as dom|res|rcode -> timestamp ( * 86400)

Fast queries:
=============
- we can provide fast query by cluserid/rcode
- we can provide fast query by domain
- we can provide query by ip
- we will return count, last seen, first seen for domain.



NODEJS code is old and not maintained. kept for historical reasons
=================


install nodejs and npm
install rabbitmq
install solr and redis
edit config/config.js to point to your location. (multi-node analyzer is possible, as long as they connect to the same mq)

run npm install

run dnsindex.js on machine that receives dns traffic

run dnsstore.js on every analyzer node

