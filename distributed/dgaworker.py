#!/usr/bin/env python

import logging
import time
import tldextract
import dnslib
import base64
import ConfigParser as CFG
import redis
import numpy as np
import zmq

import pika
import datetime
import math
import string
import json
from dgascore import DGAScore

tldextract.PUBLIC_SUFFIX_LIST_URLS=["file:///data/effective_tld_names01.dat", "file:///data/effective_tld_names02.dat"]

dgascore = DGAScore()

def get_date():
    d = datetime.datetime.now()
    return "%s-%s-%s" % (d.day, d.month, d.year)

def cluster_id(domain_label):
    dom = tldextract.extract(domain_label)
    line = "%s.%s." % (dom.domain, dom.suffix)
    domain =  dom.domain.encode('utf-8')
    zone = "nozone"
    if len(dom.suffix) > 1:
       zone = dom.suffix.encode('utf-8')
    try:
        zone = domain[domain.rindex('.')+1:]
    except Exception, e:
        pass
    c =  "%s_%.2i_%s_%.2i_%s_%s" % (zone, len(domain), charset(domain), len(dom.subdomain), charset(dom.subdomain.encode('utf-8')), entropy(domain))
    return c

def features(dom_label):
    dom = tldextract.extract(dom_label)
    domain =  dom.domain.encode('utf-8')
    return [len(domain), len(dom.subdomain), len(dom.suffix), entropy(domain)] + stats(domain)  + stats(dom.subdomain.encode('utf-8'))

def stats(s):
    return [ len(s.translate(None, "%s%s" % (string.lowercase, string.punctuation))),
             len(s.translate(None, "%s%s" %(string.lowercase, string.digits))),
             len(s.translate(None, string.digits + string.punctuation))]


def charset(s):
# test 1 - would domain contain punctuation
# test 2 - would domain contain numbers
# test 3 - is domain letter only
    c = ""
    s = s.lower()
    c = "N%.2i"%(len(s.translate(None, "%s%s" % (string.lowercase, string.punctuation))))
    c = "%sP%.2i"% (c, len(s.translate(None, "%s%s" %(string.lowercase, string.digits))))
    c = "%sA%.2i"%(c, len(s.translate(None, string.digits + string.punctuation)))
    return c

def should_ignore(name):
    ign = ["amazon", "vk.me","yahoo.com", "vk.com", "yahoodns", "google.com", ".dlink", ".local", "yotaaccessinterface", ".mail-abuse.org", ".dnsbl.void.ru", ".relays.visi.com", ".spamhaus", ".blitzed.org", "csplc.org", "njabl.org", "userapi.com", "dsbl.org", ".barracudacentral", ".dnsbl.", "akamai", "lxdns", "kenetic", "keenetic", "cloudfront", "dnw.bz", "in-addr", "g0v.tw", "nlink","m6r.eu", "am15.net", "xn--"]
    for f in ign:
        if name.lower().find(f) != -1:
            return True

    return False

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
    #count, bins = np.histogram(x)
    count = x
    p = np.ma.fix_invalid(count/float(np.sum(count)))
    return (-np.sum(np.compress(p != 0, p*(np.log(p)))))
    #return np.log2(np.max(x))*np.sum(x * np.log2(x+0.000001))
    #return np.sum(-x * np.log2(x + 0.1))

def calc_period(arr):
    if len(arr) <20:
        return 1.0 # low periodicy/high score
    a = np.array(arr, dtype='i4')
    df = np.diff(a)
# to clarify
    #p = 1 - calc_entropy(df)/np.sum(df)/len(df)
    #p =  calc_entropy(df)/np.sum(df)/len(df)/len(df)
    p =  1-(10 *calc_entropy(df)/np.log(np.exp(len(df))))
    return p


def verotkl(s):
    if len(s) < 3:
        return 0.0
    a = np.ma.fix_invalid(np.array(s, dtype='i4'))
    median = np.median(a)
    diff = median - a
    abs =np.sum( a * a)
    return np.ma.fix_invalid([np.sqrt(2*abs/len(a) - 1/median)]).data[0]

def indcallback(ch, method, properties, body):

    global rediscl
    try:
        pack = json.loads(body)
                
        if pack["rtype"] != "A":
            return
        if should_ignore(pack["qname"]):
            return
        pack["cluster"] = cluster_id(pack["qname"])
        rediscl.rpush("t:%s"% (pack["cluster"]), int(time.time()))
        #rediscl.expire("t:%s" % (pack["cluster"]), 600)
        if rediscl.llen("t:%s"% (pack["cluster"])) > 200: # max - keep 20 timestamps
            rediscl.lpop("t:%s"% (pack["cluster"]))
        periods = rediscl.lrange("t:%s" % pack["cluster"], 0, -1)
        rediscl.sadd("s:%s" %pack["sender"], pack["cluster"])
        pack["score"] = [dscore(pack["qname"]),
		         calc_period(periods),
                         verotkl(periods),
                         int(pack["dns-qdcount"]), int(pack["dns-ancount"]), 
                         int(pack["dns-nscount"]), int(pack["dns-arcount"]), int(pack["dns-ttl"])] + features(pack["qname"])
        
        if (pack["score"][0] > -1):
            if pack["rcode"] != 0:
                print "%s s:%s rc: %s  cluster: %s" % (pack["qname"], json.dumps(pack["score"]), pack["rcode"],  pack["cluster"])
                rediscl.sadd("c:%s"%pack["cluster"], pack["qname"])
            else:
                print "%s s:%s rc: %s r: %s  cluster: %s" % (pack["qname"], json.dumps(pack["score"]), pack["rcode"], pack["response"],  pack["cluster"])
                rediscl.sadd("i:%s"% pack["response"], pack["qname"])
        #set with expiration
        rediscl.setex("h:%s" % pack["qname"], json.dumps(pack), 60)
            
    except KeyError, e:
        print e


if __name__ == "__main__":
    config = CFG.ConfigParser()
    logger = logging.getLogger()
    config.read("dnsdexer.cfg")
    rediscl = redis.Redis(host = config.get("main","redishost"),
                          port = int(config.get("main", "redisport")))
    print config.get("main", "queue")

    if config.get("main", "queue") == "amqp":
        print config.get("amqp", "host")
        amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"),
                                                                     int(config.get("amqp", "port")),"/"))
        amqpchann = amqpconn.channel()
        amqpexchange = config.get("amqp", "packetex")
        amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')
        amqpchann.queue_declare(queue='dga')
        amqpchann.queue_bind(exchange = amqpexchange, queue='dga')
        amqpchann.basic_consume(indcallback, queue='dga', no_ack = True)
        amqpchann.start_consuming()

    if config.get("main", "queue") == "zmq":
        print config.get("zmq", "host")
        context = zmq.Context()
        zmq_socket = context.socket(zmq.PULL)
        zmq_socket.connect(config.get("zmq", "host"))
        while True:
            indcallback(None, None, None, zmq_socket.recv())

            
