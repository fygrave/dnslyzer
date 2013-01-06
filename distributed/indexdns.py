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

celery = Celery()
celery.config_from_object('celeryconfig')

def getredis():
    config = CFG.ConfigParser()
    config.read("dnsdexer.cfg")
    r = redis.Redis(host = config.get("main","redishost"), port = config.get("main", "redisport"))
    return r

def get_date():
    d = datetime.datetime.now()
    return "%s-%s-%s" % (d.day, d.month, d.year)

def cluster_id(domain):
    zone = domain[domain.rindex('.'):]
    return "%s_%s" % (zone, domain.length)


@celery.task
def indexp(pack):
    logger = logging.getLogger()
    logger.info("got dnspack")
    print base64.b64decode(pack).encode('hex')
    dnspack = base64.b64decode(pack)[12:]
    r = dnslib.DNSRecord.parse(dnspack)
    if r.header.rcode != 0:
        if r.q.qtype == 'A':
            key =  "%s:%s:%s:%s" %(r.q.qname, cluster_id(r.q.qname), get_date(), r.header.rcode)
            red = getredis()
            red.set(key, dnspack.encode('hex'))
    for frecord in r.rr:
        if frecord.rtype == 'A':
            key =  "%s:%s:%s:%s" %(frecord.get_rname(), cluster_id(frecord.get_rname()), get_date(), r.header.rcode)
            key2 =  "%s;%s;%s" %(frecord.rdata, frecord.get_rname(), get_date())
            red.set(key, dnspack.encode('hex'))
            red.set(key2, dnspack.encode('hex'))
            print frecord
        #print frecord



if __name__ == '__main__':
    getredis()
    tasks.register(indexp)
    celery.worker_main()
