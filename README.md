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


running the NODEJS code
=================


install nodejs and npm
install rabbitmq
install solr and redis
edit config/config.js to point to your location. (multi-node analyzer is possible, as long as they connect to the same mq)

run npm install

run dnsindex.js on machine that receives dns traffic

run dnsstore.js on every analyzer node

