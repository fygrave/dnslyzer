#!/usr/bin/env python
import SocketServer
import time
import dnslib
import ConfigParser as CFG
import logging
import pika
import base64
import argparse


config = None




class DNSReceiver(SocketServer.BaseRequestHandler):
    config = None
    amqpconn = None
    amqpchann = None
    anqpexchange = None


    def __init__(self, request, client_address, server):
        self.config = config
        logger = logging.getLogger()
        logger.info("Server started")
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        self.amqpconn = pika.BlockingConnection(pika.ConnectionParameters(self.config.get("amqp", "host"), int(self.config.get("amqp", "port")), "/"))
        self.amqpchann = self.amqpconn.channel()
        self.amqpexchange = self.config.get("amqp", "packetex")
        self.amqpchann.exchange_declare(exchange=self.amqpexchange, type='fanout')
        return

    def parsepack(self, data):
        dnspack = data[12:]
        r = dnslib.DNSRecord.parse(dnspack)
        if r.header.rcode != 0:
            if r.q.qtype == 1:
                pack =  {"qname": "%s"%r.q.qname, "response": "",  "rcode": r.header.rcode, "sender": "127.0.0.1", "time": time.time()}
                self.amqpchann.basic_publish(exchange = self.amqpexchange, routing_key="%s.%s.unknown" % (pack["qname"], pack["rcode"]),
                        body = json.dumps(pack))

        for frecord in r.rr:
            if frecord.rtype == 1:
                pack =  {"qname": "%s"% frecord.get_rname(),   "rcode": r.header.rcode, "sender": "127.0.0.1", "time": time.time(), "response":"%s"%frecord.rdata}
                self.amqpchann.basic_publish(exchange = self.amqpexchange, routing_key="%s.%s.%s" % (pack["qname"],  pack["rcode"], pack["response"]),
                        body = json.dumps(pack))



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
