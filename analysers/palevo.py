#!/usr/bin/env python

import redis
import re
import json
import sys


import argparse

parser = argparse.ArgumentParser(description='Map botnet domains in DNS zone')
parser.add_argument('zone', metavar='zone', type=str, nargs=1,
                   help='DNS zone (i.e. eu, org, com)')
args = parser.parse_args()

r = redis.StrictRedis(host='localhost', port=6381, db=0)
print " digraph dns { scmap = true; nodesep = 0.15; node [style=filled];"
print "graph [label=\"Zone %s analysis\", fontsize=8];" % args.zone[0]




#cluster_pattern = "*.eu:eu*:2"
cluster_pattern = "*.%s:%s*:2"% (args.zone[0], args.zone[0])
clusters = {}
cluster_doms = {}

def analyse_by_ip(ip):
    hosts = r.keys("%s;*"%ip)
    for i in hosts:
        rez = re.search("(.*);(.*)", i)
        print "\"%s\" -> \"%s\";" % (rez.group(1), rez.group(2))

def analyse_cluster(clu):
    cdoms = r.keys("*:%s:*" % clu)
    for dz in cdoms:
        if re.search(':0$',  dz): # look for successeful queries
            rez = r.hmget(dz, "query", "firstseen", "lastseen", "count")
            query = json.loads(rez[0])
            if len(query["query"]) > 0 and len(query["response"]) > 0:
                print "\"%s\" -> \"%s\";" %(query["query"][0], query["response"][0]) # assume all packets had one IP
                analyse_by_ip(query["response"][0])

doms = r.keys(cluster_pattern)

for a in doms:
    d = re.search('(.*):(.*):.*', a)
    cluster_id = d.group(2)
    domain = d.group(1)
    if clusters.has_key(cluster_id):
        clusters[cluster_id] = clusters[cluster_id] + 1
        cluster_doms[cluster_id].append(domain)
    else:
        clusters[cluster_id] = 1
        cluster_doms[cluster_id] = []
        cluster_doms[cluster_id].append(domain)

#print "matching clusters %s" %clusters

for cl in clusters.keys():
    if clusters[cl] > 5:
        #print "Processing cluster %s" % cl
        for dom in cluster_doms[cl]:
            print "\"%s\" -> \"%s\";"  % (dom, cl)
        analyse_cluster(cl)



print "}"
