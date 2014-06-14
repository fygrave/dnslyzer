#!/usr/bin/env python

import logging
import time
import tldextract
import dnslib
import base64
import ConfigParser as CFG
import redis

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
    ign = ["amazon", "vk.me","yahoo.com", "vk.com", "yahoodns", "google.com", ".dlink", ".local", "yotaaccessinterface", ".mail-abuse.org", ".dnsbl.void.ru", ".relays.visi.com", ".spamhaus", ".blitzed.org", "csplc.org", "njabl.org", "userapi.com", "dsbl.org", ".barracudacentral", ".dnsbl.", "akamai", "lxdns", "kenetic", "keenetic", "cloudfront", "dnw.bz", "in-addr", "g0v.tw", "nlink","m6r.eu"]
    for f in ign:
        if name.lower().find(f) != -1:
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

def dscore(line):
    if len(line) < 5:
        return 0
    dom = tldextract.extract(line)
    line = "%s.%s." % (dom.domain, dom.suffix)

    score = dgascore.score_for_string(line)

    #perp = dgascore.perplexity_for_string(line)
    return score

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
    try:
        pack = json.loads(body)
        if should_ignore(pack["qname"]):
            return
        pack["cluster"] = cluster_id(pack["qname"])
        score = dscore(pack["qname"])
        if (score > 90):
            if pack["rcode"] != 0:
                print "%s s:%s rc: %s cluster: %s" % (pack["qname"], score, pack["rcode"], pack["cluster"])
                rediscl.sadd("c:%s"%pack["cluster"], pack["qname"])
            else:
                print "%s s:%s rc: %s r: %s cluster: %s" % (pack["qname"], score, pack["rcode"], pack["response"], pack["cluster"])
                rediscl.sadd("i:%s"% pack["response"], pack["qname"])
    except Exception, e:
        print e


config = CFG.ConfigParser()
config.read("dnsdexer.cfg")
print config.get("amqp", "host")
amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"), int(config.get("amqp", "port")), "/"))
amqpchann = amqpconn.channel()
amqpexchange = config.get("amqp", "packetex")
amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')


logger = logging.getLogger()
amqpchann.queue_declare(queue='dga')
amqpchann.queue_bind(exchange = amqpexchange, queue='dga')
rediscl = redis.Redis(host = config.get("main","redishost"), port = int(config.get("main", "redisport")))

amqpchann.basic_consume(indcallback, queue='dga', no_ack = True)
amqpchann.start_consuming()
