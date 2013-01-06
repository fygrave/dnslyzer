#!/usr/bin/env python
import SocketServer
import ConfigParser as CFG
import logging




class DNSReceiver(SocketServer.BaseRequestHandler):


    def handle(self):
        logger = logging.getLogger()
        data = self.request[0]
        logger.info("%s" % self.client_address[0])


if __name__ == "__main__":
    config = CFG.ConfigParser()
    config.read("dnsdexer.cfg")
    HOST, PORT = "0.0.0.0", int(config.get("main", "dnsport"))
    server = SocketServer.UDPServer((HOST, PORT), DNSReceiver)
    server.serve_forever()
