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
    c =  "%s_%s" % (zone, len(domain))
    return c


@celery.task
def indexp(pack):
    print "doing index"
    global rediscl
    logger = logging.getLogger()
    logger.info("got dnspack")
    #print base64.b64decode(pack).encode('hex')
    dnspack = base64.b64decode(pack)[12:]
    try:
        r = dnslib.DNSRecord.parse(dnspack)
        if r.header.rcode != 0:
            if r.q.qtype == 1:
                key =  "%s:%s:%s" %(r.q.qname, cluster_id(r.q.qname), r.header.rcode)
                red = rediscl
                red.hmset(key, {'raw':dnspack.encode('hex'), 'date': datetime.datetime.now()})
        for frecord in r.rr:
            if frecord.rtype == 1:
                key =  "%s:%s:%s" %(frecord.get_rname(), cluster_id(frecord.get_rname()), r.header.rcode)
                key2 =  "%s;%s" %(frecord.rdata, frecord.get_rname())
                red = rediscl
                v = red.hmget(key, "count")
                count = 1
                firstseen = datetime.datetime.now()
                if v[0] != None:
                    print v[0]
                    count = count + int(v[0])
                    firstseen = red.hmget(key, "firstseen")

                print 'count %i ' % (count)
                red.hmset(key, {'raw':dnspack.encode('hex'), 'firstseen': firstseen, 'lastseen': datetime.datetime.now(), 'count': count} )
                red.set(key2, dnspack.encode('hex'))
    except Exception, e:
        print "Error: %s while parsing %s" % (e, dnspack.encode('hex'))



if __name__ == '__main__':
    getredis()
    tasks.register(indexp)
    celery.worker_main()
