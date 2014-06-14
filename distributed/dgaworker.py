#!/usr/bin/env python

import logging
import time
import dnslib
import base64
import ConfigParser as CFG

import pika
import datetime
import math
import string
import json
from dgascore import DGAScore

dgascore = DGAScore()

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

def score(line):
    if line[len(line) - 1] != '.':
        line = "%s." % line
    score = dgascore.score_for_string(line)
    perp = dgascore.perplexity_for_string(line)
        
def entropy(string):
    "Calculates the Shannon entropy of a string"

    # get probability of chars in string
    prob = [ float(string.count(c)) / len(string) for c in dict.fromkeys(list(string)) ]

    # calculate the entropy
    entropy = - sum([ p * math.log(p) / math.log(2.0) for p in prob ])

    return round(entropy)

def redisUpdate(dom, dat, cluster, rtype, rcode, skey, lkey):
    timestamp = int(int(time.time())) # care for day only
    rediscl.sadd("@%s"%dom, "%s:%s:%s" %(rtype, dat, rcode))
    if dat != '_':
        rediscl.sadd("&%s"%dat, "%s:%s" % (rtype, dom))
    rediscl.sadd("$%s$%s"% (cluster, rcode), dom)
    rediscl.incr("%s:%s"% (dom, dat))
    rediscl.set(lkey, timestamp)
    if not rediscl.exists(skey):
        rediscl.set(skey,timestamp)
    return 0

def indcallback(ch, method, properties, body):

    global rediscl
    pack = json.loads(body)
    pack["cluster"] = cluster_id(pack["qname"])
    score = score(pack["qname"])
    if (score > 1):
        if pack["rcode"] != 0:
            print "%s s:%s rc: %s cluster: %s" % (pack["qname"], score, pack["rcode"], pack["cluster"])
        else:
            print "%s s:%s rc: %s r: %s cluster: %s" % (pack["qname"], score, pack["rcode"], pack["response"], pack["cluster"])


config = CFG.ConfigParser()
config.read("dnsdexer.cfg")
print config.get("amqp", "host")
amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"), int(config.get("amqp", "port")), "/"))
amqpchann = amqpconn.channel()
amqpexchange = config.get("amqp", "packetex")
amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')
rediscl = redis.Redis(host = config.get("main","redishost"), port = int(config.get("main", "redisport")))

logger = logging.getLogger()
amqpchann.queue_declare(queue='redis')
amqpchann.queue_bind(exchange = amqpexchange, queue='redis')

amqpchann.basic_consume(indcallback, queue='redis', no_ack = True)
amqpchann.start_consuming()
