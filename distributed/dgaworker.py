#!/usr/bin/env python

import logging
import time
import tldextract
import dnslib
import base64
import ConfigParser as CFG
import redis
import numpy as np

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
    ign = ["amazon", "vk.me","yahoo.com", "vk.com", "yahoodns", "google.com", ".dlink", ".local", "yotaaccessinterface", ".mail-abuse.org", ".dnsbl.void.ru", ".relays.visi.com", ".spamhaus", ".blitzed.org", "csplc.org", "njabl.org", "userapi.com", "dsbl.org", ".barracudacentral", ".dnsbl.", "akamai", "lxdns", "kenetic", "keenetic", "cloudfront", "dnw.bz", "in-addr", "g0v.tw", "nlink","m6r.eu", "am15.net", "xn--"]
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
    rediscl.rpush("&%s$%s"% (cluster), int(time.time()))
    rediscl.incr("%s:%s"% (dom, dat))
    rediscl.set(lkey, timestamp)
    if not rediscl.exists(skey):
        rediscl.set(skey,timestamp)
    return 0

def calc_entropy(x):
    return np.log2(np.max(x))*np.sum(x * np.log2(x+0.000001))
    #return np.sum(-x * np.log2(x + 0.1))

def calc_period(arr):
    if len(arr) <2:
        return 100 # low periodicy/high score
    a = np.array(arr, dtype='i4')
    df = np.diff(a)
# to clarify
    #p = 1 - calc_entropy(df)/np.sum(df)/len(df)
    p =  calc_entropy(df)/np.sum(df)/len(df)/len(df)
    return p

def indcallback(ch, method, properties, body):

    global rediscl
    try:
        pack = json.loads(body)
        if pack["rtype"] != "A":
            return
        if should_ignore(pack["qname"]):
            return
        pack["cluster"] = cluster_id(pack["qname"])
        score = dscore(pack["qname"])
        rediscl.rpush("t:%s"% (pack["cluster"]), int(time.time()))
        #rediscl.expire("t:%s" % (pack["cluster"]), 600)
        if rediscl.llen("t:%s"% (pack["cluster"])) > 20: # max - keep 20 timestamps
            rediscl.lpop("t:%s"% (pack["cluster"]))
        pscore = calc_period(rediscl.lrange("t:%s" % pack["cluster"], 0, -1))
        if (score > 90):
            if pack["rcode"] != 0:
                print "%s s:%s rc: %s p: %s cluster: %s" % (pack["qname"], score, pack["rcode"], pscore, pack["cluster"])
                rediscl.sadd("c:%s"%pack["cluster"], pack["qname"])
            else:
                print "%s s:%s rc: %s r: %s p: %s cluster: %s" % (pack["qname"], score, pack["rcode"], pack["response"], pscore, pack["cluster"])
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
