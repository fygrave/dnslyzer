#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis

import IPy
import re
import datetime
import time
import json

class WhoisQuery():


    def __init__(self,  host, port):
        self.redis_whois_server = redis.Redis(host= host, port = port)

    def list_to_str(self, dom,  l):
        if len(l) == 0:
            return None
        return reduce(lambda x, y: "%s\r\n\r\n%s"%(x,y), map(self.printable_entry, map(lambda x: (dom, x), l)))

    def printable_entry(self,  v):
        dom = v[0]
        val = v[1]
        d = val.split(':')
        rtype = 'A'
        skey = ''
        lkey = ''
        ckey = ''
        r = {}
        if len(d) == 3: # host
            rtype = d[0]
            skey = "%s;%s;%s" % (dom, d[1], d[2])
            lkey = "%s|%s|%s" % (dom, d[1],d[2])
            ckey = "%s:%s" % (dom, d[1])
            r["rrname"] = dom
            r["rdata"] = d[2]
        else:
            skey = "%s;%s;%s" % (d[1],dom,"0")
            lkey = "%s|%s|%s" % (d[1],dom,"0")
            ckey = "%s:%s" % (d[1], dom)
            r["rrname"] = d[1]
            r["rrtype"] = d[0]
            r["rdata"] = dom
        r["rrtype"] = rtype
        try:
            r["time_first"] =  datetime.datetime.fromtimestamp(int(self.redis_whois_server.get(skey)) * 86400 + 86400).strftime("%Y-%m-%d 00:00:00")
            r["time_last"] = datetime.datetime.fromtimestamp(int(self.redis_whois_server.get(lkey)) * 86400 + 86400).strftime("%Y-%m-%d 00:00:00")
            r["count"] = self.redis_whois_server.get(ckey)
        except Exception, e:
            print e
            print "%s rdata: %s skey: %s lkey: %s ckey: %s" % (r["rrname"], r["rdata"], skey, lkey, ckey)
            # default if keys not found
            return ""
            #r["time_first"] = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d 00:00:00")
            #r["time_last"] = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d 00:00:00")
            #r["count"] = 1

        return json.dumps(r, sort_keys = True, indent=4, separators=(',', ': '))

    def whois_host(self, query):
        to_return = self.list_to_str(query, self.redis_whois_server.smembers("@%s"%query))
        if to_return is None:
            to_return = 'Host not found.\n'
        #else:
        #    to_return += self.get_all_informations(query)
        return to_return

    def whois_ip(self, ip):
        ip = IPy.IP(ip)
        print ip
        to_return = self.list_to_str(str(ip), self.redis_whois_server.smembers("&%s"%str(ip)))
        if not to_return:
            to_return = 'IP ' + str(ip) + ' not found.\n'
        #else:
        #    to_return += self.get_all_informations(key)
        return to_return


if __name__ == "__main__":
    import os
    import IPy
    import sys
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read("../../etc/whois-server.conf")
    query_maker = WhoisQuery(int(config.get('whois_server','redis_db')), config.get('whois_server','prepend_to_keys'))

    def usage():
        print "arin_query.py query"
        exit(1)

    if len(sys.argv) < 2:
        usage()

    query = sys.argv[1]
    ip = None
    try:
        ip = IPy.IP(query)
    except:
        pass


    if ip:
        print(query_maker.whois_ip(ip))
    else:
       print(query_maker.whois_asn(query))
