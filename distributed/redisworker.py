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




def get_date():
    d = datetime.datetime.now()
    return "%s-%s-%s" % (d.day, d.month, d.year)

def cluster_id(domain_label):
    domain = "%s" % (domain_label)
    zone = "nozone"
    try:
        zone = domain[domain.rindex('.')+1:]
    except Exception, e:
        pass
    c =  "%s_%s_%s" % (zone, len(domain), entropy(domain))
    return c

def should_ignore(name):
    ign = [".Dlink", ".local", "yotaaccessinterface", ".mail-abuse.org", ".dnsbl.void.ru", ".relays.visi.com", ".spamhaus", ".blitzed.org", "csplc.org", "njabl.org", "userapi.com", "dsbl.org", ".barracudacentral", ".dnsbl."]
    for f in ign:
        if name.find(f) != -1:
            return True

    return False

def charset(s):
# test 1 - would domain contain punctuation
# test 2 - would domain contain numbers
# test 3 - is domain letter only
    s = s.translate(".")
    c = ""
    s = s.lower()
    if len(s.translate("%s%s" %(string.lowercase, string.digits))) != 0:
        c = "N"
    else:
        c = "X"
    if len(s.translate("%s%s" % (string.lowercase, string.punctuation))) != 0:
        c = "%sP"%c
    else:
        c ="%sX"%c
    if len(s.translate(string.lowercase)) == 0:
        c = "%sA"%c
    else:
        c ="%sX"%c

    return c

def entropy(string):
    "Calculates the Shannon entropy of a string"

    # get probability of chars in string
    prob = [ float(string.count(c)) / len(string) for c in dict.fromkeys(list(string)) ]

    # calculate the entropy
    entropy = - sum([ p * math.log(p) / math.log(2.0) for p in prob ])

    return round(entropy)



def indcallback(ch, method, properties, body):
    global rediscl
    logger = logging.getLogger()
    logger.info("got dnspack")
    pack = json.loads(body)
    pack["cluster"] = cluster_id(pack["qname"])
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
