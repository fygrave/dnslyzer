#!/usr/bin/env python

import logging
import dnslib
import base64
import ConfigParser as CFG
from pyes import *
import pika
import datetime
import math
import string
import json
from birch import *



root = Node()
global root

def entropy(string):
    "Calculates the Shannon entropy of a string"

    # get probability of chars in string
    prob = [ float(string.count(c)) / len(string) for c in dict.fromkeys(list(string)) ]

    # calculate the entropy
    entropy = - sum([ p * math.log(p) / math.log(2.0) for p in prob ])

    return round(entropy)



def indcallback(ch, method, properties, body):

    pack = json.loads(body)
    v = Vector()
    v.domain = pack["qname"]
    v[0] = entropy(pack["qname"])
    v[1] = len(pack["qname"])
    v[2] = pack["rcode"]
    root.trickle(v)
    print root




config = CFG.ConfigParser()
config.read("dnsdexer.cfg")
print config.get("amqp", "host")
amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"), int(config.get("amqp", "port")), "/"))
amqpchann = amqpconn.channel()
amqpexchange = config.get("amqp", "packetex")
amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')


amqpchann.queue_declare(queue='classify', auto_delete = True)
amqpchann.queue_bind(exchange = amqpexchange, queue='classify')

amqpchann.basic_consume(indcallback, queue='classify', no_ack = True)
amqpchann.start_consuming()
root = Node()
