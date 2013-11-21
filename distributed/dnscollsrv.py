#!/usr/bin/env python
import SocketServer
import time
import dnslib
import ConfigParser as CFG
import logging
import pika
import base64
import argparse
import json


global config
parser = argparse.ArgumentParser(description='Capture DNS forward packets')
parser.add_argument('config', type=file, help= 'config file')
parser.set_defaults(config = "dnsdexer.cfg")
r = parser.parse_args()
config = CFG.ConfigParser()
config.readfp(r.config)

# QRTYPE array taken from: https://github.com/ruletko/pydnsd/blob/master/server.py
QRTYPE = [ 'U', #0
          'A', #1 a host address
          'NS', #2 an authoritative name server
          'MD', #3 a mail destination (Obsolete - use MX)
          'MF', #4 a mail forwarder (Obsolete - use MX)
          'CNAME', #: 5, # the canonical name for an alias
          'SOA', # 6, # marks the start of a zone of authority
          'MB', #7 # a mailbox domain name (EXPERIMENTAL)
          'MG', #: 8, # a mail group member (EXPERIMENTAL)
          'MR', #: 9, # a mail rename domain name (EXPERIMENTAL)
          'NULL', #: 10, # a null RR (EXPERIMENTAL)
          'WKS', #: 11, # a well known service description
          'PTR', #: 12, # a domain name pointer
          'HINFO', #: 13, # host information
          'MINFO', #: 14, # mailbox or mail list information
          'MX' , #: 15, # mail exchange
          'TXT', #: 16, # text strings
          #'AXFR', #: 252, # A request for a transfer of an entire zone
          #'MAILB': 253, # A request for mailbox-related records (MB, MG or MR)
          #'MAILA': 254, # A request for mail agent RRs (Obsolete - see MX)
          #'*': 255, # A request for all records
         ]

class DNSReceiver(SocketServer.BaseRequestHandler):
    conf = config

    amqpconn = pika.BlockingConnection(pika.ConnectionParameters(config.get("amqp", "host"), int(config.get("amqp", "port")), "/"))
    amqpchann = amqpconn.channel()
    amqpexchange = config.get("amqp", "packetex")
    amqpchann.exchange_declare(exchange=amqpexchange, type='fanout')

    def __init__(self, request, client_address, server):
        logger = logging.getLogger()
        logger.info("Server started")
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        return

    def parsepack(self, data):
      try:
        dnspack = data[12:]
        r = dnslib.DNSRecord.parse(dnspack)
        if r.header.rcode != 0:
            if r.q.qtype < 17 and r.q.qtype != 12: # we dont want PTR
                pack =  {"qname": "%s"%r.q.qname, "response": "", "rtype": QRTYPE[int(r.q.qtype)], "rcode": r.header.rcode, "sender": "127.0.0.1", "time": int(time.time())}
                self.amqpchann.basic_publish(exchange = self.amqpexchange, routing_key="%s.%s.unknown" % (pack["qname"], pack["rcode"]),
                        body = json.dumps(pack))

        for frecord in r.rr:
            if frecord.rtype < 17 and frecord.rtype != 12: # we dont want PTR
                pack =  {"qname": "%s"% frecord.get_rname(), "rtype": QRTYPE[int(frecord.rtype)],   "rcode": r.header.rcode, "sender": "127.0.0.1", "time": int(time.time()), "response":"%s"%frecord.rdata}
                self.amqpchann.basic_publish(exchange = self.amqpexchange, routing_key="%s.%s.%s" % (pack["qname"],  pack["rcode"], pack["response"]),
                        body = json.dumps(pack))
      except Exception, e:
          print base64.b64encode(data)
          print  e



    def handle(self):
        logger = logging.getLogger()
        data = self.request[0]
        logger.info("%s" % self.client_address[0])
        self.parsepack(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Capture DNS forward packets')
    parser.add_argument('config', type=file, help= 'config file')
    parser.set_defaults(config = "dnsdexer.cfg")
    r = parser.parse_args()
    print r.config
    global config


    config = CFG.ConfigParser()
    config.readfp(r.config)
    HOST, PORT = "0.0.0.0", int(config.get("main", "dnsport"))
    server = SocketServer.UDPServer((HOST, PORT), DNSReceiver)
    server.confg = config
    server.serve_forever()
