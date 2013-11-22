#!/usr/bin/python
# -*- coding: utf-8 -*-

import redis

import IPy
import re

class WhoisQuery():


    def __init__(self,  host, port):
        self.redis_whois_server = redis.Redis(host= host, port = port)

    def list_to_str(self, l):
        if len(l) == 0:
            return None
        return reduce(lambda x, y: "%s\n%s"%(x,y), l)
    def whois_host(self, query):
        to_return = self.list_to_str(self.redis_whois_server.smembers("@%s"%query))
        if to_return is None:
            to_return = 'Host not found.\n'
        #else:
        #    to_return += self.get_all_informations(query)
        return to_return

    def __find_best_range(self, ip):
        to_return = None
        ranges = None
        key = str(ip)
        if self.ipv4 :
            regex = '.*[.]'
        else:
            regex = '.*[:]'
        while not ranges:
            key = re.findall(regex, key)
            if len(key) != 0:
               key = key[0][:-1]
            else:
                break
            ranges = self.redis_whois_server.smembers(self.prepend + key)
        best_range = None
        for range in ranges:
            splitted = range.split('_')
            ip_int = ip.int()
            if int(splitted[0]) <= ip_int and int(splitted[1]) >= ip_int:
                if best_range is not None:
                    br_splitted = best_range.split('_')
                    if int(splitted[0]) > int(br_splitted[0]) and int(splitted[1]) < int( br_splitted[1]):
                        best_range = range
                else:
                    best_range = range
        if best_range is not None:
            to_return = self.redis_whois_server.get(best_range)
        return to_return

    def get_all_informations(self, key):
        to_return = ''
        for subkey in self.subkeys:
            list = self.redis_whois_server.smembers(key + subkey)
            for element in list:
                value = self.redis_whois_server.get(element)
                if value is not None:
                    to_return += '\n' + value
        return to_return

    def whois_ip(self, ip):
        ip = IPy.IP(ip)
        print ip
        to_return = self.list_to_str(self.redis_whois_server.smembers("&%s"%str(ip)))
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
