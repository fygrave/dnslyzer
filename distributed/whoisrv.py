#!/usr/bin/python

# built on the top of https://github.com/Rafiot/Whois-Server/
import sys
import os
import ConfigParser

location = os.getcwd() + "/aha"
if '__file__' in dir():
    location = __file__

sys.path.append(os.path.dirname(os.path.abspath(location)))
sys.path.append(os.path.dirname(os.path.join(os.path.abspath(location),'lib')))

config = ConfigParser.RawConfigParser()
config.read("whois-server.conf")

import syslog
syslog.openlog('Whois_Queries', syslog.LOG_PID, syslog.LOG_USER)


redis_db = int(config.get('whois_server','redis_db'))
host = config.get('whois_server','listen')
redis_host = config.get('whois_server','redis_host')
redis_port = int(config.get('whois_server','redis_port'))
port = int(config.get('whois_server','port_query'))

import SocketServer
from lib.queries.whois_query import *

class WhoisServer(SocketServer.BaseRequestHandler ):
    def handle(self):
        syslog.syslog(syslog.LOG_INFO, self.client_address[0] + ' is connected' )
        query_maker = WhoisQuery(redis_host, redis_port)
        queries = 0
        query = self.request.recv(1024).strip()
        if query == '':
	    syslog.syslog(syslog.LOG_DEBUG, self.client_address[0] + ' is gone' )
            self.request.send('no data\n\n')
            return
            
        ip = None
        syslog.syslog(syslog.LOG_DEBUG, 'Query of ' + self.client_address[0] + ': ' + query)
        queries += 1
        try:
	    ip = IPy.IP(query)
        except:
	    pass
        if ip:
	    response = query_maker.whois_ip(ip)
        else:
           response = query_maker.whois_host(query)
        self.request.send(response + '\n\n')



SocketServer.ThreadingTCPServer.allow_reuse_address = True
server = SocketServer.ThreadingTCPServer((host, port), WhoisServer)
server.serve_forever()
