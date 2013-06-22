#!/usr/bin/env python

from celery import Celery
from celery.task import Task
from celery.registry import tasks
import logging
import dnslib
import base64
import ConfigParser as CFG
from voltdbclient import *
import datetime

celery = Celery()
celery.config_from_object('celeryconfig')



from celery.signals import worker_init

rediscl = None

@worker_init.connect
def on_init(signal, sender ):
    global rediscl
    rediscl =  getredis()



def getvolt():
    config = CFG.ConfigParser()
    config.read("dnsdexer.cfg")
    r =  client = FastSerializer(config.get("main","volthost"), int(config.get("main", "voltport")), config.get("main", "voltuser"), config.get("main", "voltpass"))
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
    c =  "%s_%s" % (zone, len(domain))
    return c


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
                key =  "%s:%s:%s:%s" %(r.q.qname, cluster_id(r.q.qname), get_date(), r.header.rcode)
                red = rediscl
                red.hmset(key, {'raw':dnspack.encode('hex'), 'date': datetime.datetime.now()})
        for frecord in r.rr:
            if frecord.rtype == 1:
                key =  "%s:%s:%s:%s" %(frecord.get_rname(), cluster_id(frecord.get_rname()), get_date(), r.header.rcode)
                key2 =  "%s;%s;%s" %(frecord.rdata, frecord.get_rname(), get_date())
                red = rediscl
                red.hmset(key, {'raw':dnspack.encode('hex'), 'date': datetime.datetime.now(), 'pack': "%s" % r} )
                red.set(key2, dnspack.encode('hex'))
    except Exception, e:
        print "Error: %s while parsing %s" % (e, dnspack.encode('hex'))



if __name__ == '__main__':
    getredis()
    tasks.register(indexp)
    celery.worker_main()
