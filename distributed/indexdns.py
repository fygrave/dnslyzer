#!/usr/bin/env python

from celery import Celery
from celery.task import Task
from celery.registry import tasks
import logging
import dnslib
import base64
import ConfigParser as CFG
import redis
import datetime
import math
import string

celery = Celery()
celery.config_from_object('celeryconfig')



from celery.signals import worker_init

rediscl = None

@worker_init.connect
def on_init(signal, sender ):
    print "init redis"
    global rediscl
    rediscl =  getredis()



def getredis():
    config = CFG.ConfigParser()
    config.read("dnsdexer.cfg")
    r = redis.Redis(host = config.get("main","redishost"), port = int(config.get("main", "redisport")))
    return r

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
    c =  "%s_%s_%s_%s" % (zone, len(domain), entropy(domain), charset(domain))
    return c

def should_ignore(name):
    ign = [".Dlink", ".local", "yotaaccessinterface", ".mail-abuse.org", ".dnsbl.void.ru", ".relays.visi.com", ".spamhaus", ".blitzed.org", "csplc.org", "njabl.org", "userapi.com", "dsbl.org"]
    for f in ign:
        if name.find(f) != -1:
            return True

    return False

def charset(s):
# test 1 - would domain contain punctuation
# test 2 - would domain contain numbers
# test 3 - is domain letter only
    s = s.translate(None, ".")
    c = ""
    s = s.lower()
    if len(s.translate(None, "%s%s" %(string.lowercase, string.digits))) != 0:
        c = "N"
    else:
        c = "X"
    if len(s.translate(None, "%s%s" % (string.lowercase, string.punctuation))) != 0:
        c = "%sP"%c
    else:
        c ="%sX"%c
    if len(s.translate(None, string.lowercase)) == 0:
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


@celery.task
def indexp(pack):
    global rediscl
    logger = logging.getLogger()
    logger.info("got dnspack")
    #print base64.b64decode(pack).encode('hex')
    dnspack = base64.b64decode(pack)[12:]
    try:
        r = dnslib.DNSRecord.parse(dnspack)
        if r.header.rcode != 0:
            if r.q.qtype == 1:
                key =  "%s:%s:_:%s" %(r.q.qname, cluster_id(r.q.qname), r.header.rcode)
                red = rediscl
                red.incr(key)
        for frecord in r.rr:
            if should_ignore("%s"%frecord.get_rname()):
                continue
            if frecord.rtype == 1:
                key =  "%s:%s:%s:%s" %(frecord.get_rname(), cluster_id(frecord.get_rname()), frecord.rdata, r.header.rcode)
                #key2 =  "%s;%s" %(frecord.rdata, frecord.get_rname())
                red = rediscl
                red.incr(key)
                #red.incr(key2)
    except Exception, e:
        print "Error: %s while parsing %s" % (e, dnspack.encode('hex'))



if __name__ == '__main__':
    getredis()
    tasks.register(indexp)
    celery.worker_main()
