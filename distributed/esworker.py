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




def get_date():
    d = datetime.datetime.now()
    return "%s-%s-%s" % (d.day, d.month, d.year)



def get_index():
    d = datetime.datetime.now()
    return "dnsindex_%0.2i%0.4i" % (d.month, d.year)



def indcallback(ch, method, properties, body):
    global esconn
    try:
        esconn.create_index(get_index())

        mapping = {
               u'qname': {'boost': 1.0,
                     'index': 'not_analyzed',
                     'store': 'yes',
                     'type': u'string',
                     "term_vector" : "with_positions_offsets"},
               u'rcode': {'boost': 1.0,
                     'index': 'analyzed',
                     'store': 'yes',
                     'type': u'int'},
               u'response': {'boost': 1.0,
                     'index': 'analyzed',
                     'store': 'yes',
                     'type': u'ip'
                     },
            u'lastseen': { 'boost':1.0,
                'index': 'analyzed', 'store': 'yes', 'type': 'date', 'format': 'date_time'}
                    },
            u'firstseen': { 'boost':1.0,
                'index': 'analyzed', 'store': 'yes', 'type': 'date', 'format': 'date_time'}
                    }

        esconn.put_mapping("dns_type", {'properties':mapping}, [get_index()])
    except:
        pass



    pack = json.loads(body)
    esconn.index(pack, get_index(), "dns_type")




config = CFG.ConfigParser()
config.read("dnsdexer.cfg")
print config.get("amqp", "host")
amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"), int(config.get("amqp", "port")), "/"))
amqpchann = amqpconn.channel()
amqpexchange = config.get("amqp", "packetex")
amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')
esconn = ES([config.get("main","elasticsearch")])


amqpchann.queue_declare(queue='es')
amqpchann.queue_bind(exchange = amqpexchange, queue='es')

amqpchann.basic_consume(indcallback, queue='es', no_ack = True)
amqpchann.start_consuming()
