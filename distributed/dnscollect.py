#!/usr/bin/env python
import SocketServer
import ConfigParser as CFG




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


if __name__ == "__main__":
    config = CFG.ConfigParser()
    config.read("dnsdexer.cfg")
    HOST, PORT = "localhost", int(config.get("main", "dnsport"))
    server = SocketServer.UDPServer((HOST, PORT), DNSReceiver)
    server.serve_forever()
