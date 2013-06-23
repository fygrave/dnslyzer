#!/usr/bin/env python

from celery import Celery
from celery.task import Task
from celery.registry import tasks
import logging
import dnslib
import base64
import ConfigParser as CFG
import pika
import datetime
import math
import string
import time

celery = Celery()
celery.config_from_object('celeryconfig')



from celery.signals import worker_init


amqpconn = None
amqpchann = None
amqpexchange = None


@worker_init.connect
def on_init(signal, sender ):
    print "Init"
    global amqpconn
    global amqpchann
    global amqpexchange
    config = CFG.ConfigParser()
    config.read("dnsdexer.cfg")
    amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"), int(config.get("amqp", "port")), "/"))
    amqpchann = connection.channel()
    amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')
    amqpexchange = config.get("amqp", "packetex")





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
    ign = [".Dlink", ".local", "yotaaccessinterface", ".mail-abuse.org", ".dnsbl.void.ru", ".relays.visi.com", ".spamhaus", ".blitzed.org", "csplc.org", "njabl.org", "userapi.com", "dsbl.org", ".barracudacentral", ".dnsbl."]
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
    global amqpconn
    global amqpchann
    global amqpexchange
    logger = logging.getLogger()
    logger.info("got dnspack")
    #print base64.b64decode(pack).encode('hex')
    dnspack = base64.b64decode(pack)[12:]
    try:
        r = dnslib.DNSRecord.parse(dnspack)
        if r.header.rcode != 0:
            if r.q.qtype == 1:
                pack =  {"qname": r.q.qname, "response": "", "cluster": cluster_id(r.q.qname), "rcode": r.header.rcode, "sender": "127.0.0.1", "time": time.time()}
                amqpconn.basic_publish(exchange = amqpexchange, routing_key="%s.%s.%s.unknown" % (pack["qname"], pack["cluster"], pack["rcode"]),
                        body = json.dumps(pack))

        for frecord in r.rr:
            if frecord.rtype == 1:
                key =  "%s:%s:%s:%s" %(frecord.get_rname(), cluster_id(frecord.get_rname()), frecord.rdata, r.header.rcode)
                pack =  {"qname": frecord.get_rname(),  "cluster": cluster_id(frecord.get_rname()), "rcode": r.header.rcode, "sender": "127.0.0.1", "time": time.time(), "response":frecord.rdata}
                amqpconn.basic_publish(exchange = amqpexchange, routing_key="%s.%s.%s.%s" % (pack["qname"], pack["cluster"], pack["rcode"], pack["response"]),
                        body = json.dumps(pack))
    except Exception, e:
        print "Error: %s while parsing %s" % (e, dnspack.encode('hex'))



if __name__ == '__main__':
    getredis()
    tasks.register(indexp)
    celery.worker_main()
