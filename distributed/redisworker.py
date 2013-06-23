#!/usr/bin/env python

import logging
import dnslib
import base64
import ConfigParser as CFG
import redis
import pika
import datetime
import math
import string
import json


def indcallback(ch, method, properties, body):
    global rediscl
    logger = logging.getLogger()
    logger.info("got dnspack")
    pack = json.loads(body)
    print body
    if pack["rcode"] != 0:
        key =  "%s:%s:_:%s" %(pack["qname"], pack["cluster"], pack["rcode"])
        rediscl.incr(key)
    else:
        key =  "%s:%s:%s:%s" %(pack["qname"], pack["cluster"], pack["response"], pack["rcode"])
        rediscl.incr(key)




config = CFG.ConfigParser()
config.read("dnsdexer.cfg")
print config.get("amqp", "host")
amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"), int(config.get("amqp", "port")), "/"))
amqpchann = amqpconn.channel()
amqpexchange = config.get("amqp", "packetex")
amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')
rediscl = redis.Redis(host = config.get("main","redishost"), port = int(config.get("main", "redisport")))


amqpchann.queue_declare(queue='redis')
amqpchann.queue_bind(exchange = amqpexchange, queue='redis')

amqpchann.basic_consume(indcallback, queue='redis', no_ack = True)
amqpchann.start_consuming()
