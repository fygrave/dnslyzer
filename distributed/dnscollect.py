#!/usr/bin/env python
import SocketServer
import ConfigParser as CFG
import logging
import celery
import  indexdns
import base64
import celeryconfig
import argparse


celery = celery.Celery('indexdns')
celery.config_from_object('celeryconfig')


class DNSReceiver(SocketServer.BaseRequestHandler):


    def __init__(self, request, client_address, server):
        logger = logging.getLogger()
        logger.info("Server started")
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        return


    def handle(self):
        logger = logging.getLogger()
        data = self.request[0]
        logger.info("%s" % self.client_address[0])
        print "got packet"
        indexdns.indexp.delay(base64.b64encode(data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Capture DNS forward packets')
    parser.add_argument('config', type=file, help= 'config file')
    parser.set_defaults(config = "dnsdexer.cfg")
    r = parser.parse_args()
    print r.config


    config = CFG.ConfigParser()
    config.readfp(r.config)
    HOST, PORT = "0.0.0.0", int(config.get("main", "dnsport"))
    server = SocketServer.UDPServer((HOST, PORT), DNSReceiver)
    server.serve_forever()
