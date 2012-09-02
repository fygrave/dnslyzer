dnslyzer
========

DNS traffic indexer and analyzer


This framework to store, index and analyse DNS records forwarded by DNS forwarder:
http://www.enyo.de/fw/software/dnslogger/

This code is part of passive DNS research project.



running the code
=================


install nodejs and npm
install rabbitmq
install solr and redis
edit config/config.js to point to your location. (multi-node analyzer is possible, as long as they connect to the same mq)

run npm install

run dnsindex.js on machine that receives dns traffic

run dnsstore.js on every analyzer node

