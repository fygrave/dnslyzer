#!/usr/bin/env python

import redis
import re
import json
import sys

import argparse

parser = argparse.ArgumentParser(description='Map domains related to given domain')
parser.add_argument('domain', metavar='domain', type=str, nargs=1,
                   help='DNS domain (i.e. foo.eu, foo.org, foo.com)')
args = parser.parse_args()

r = redis.StrictRedis(host='localhost', port=6381, db=0)
print " digraph dns { scmap = true; nodesep = 0.15;  outputorder = edgesfirst; node [style=filled];"
print "graph [label=\"domain %s analysis\", fontsize=8];" % args.domain[0]




#cluster_pattern = "*.eu:eu*:2"
domain_pattern = "%s*"% (args.domain[0])
reverse_pattern = "*;%s" %(args.domain[0])
clusters = {}
cluster_doms = {}

graph_set = set()




def cal_cluster(dom):
    try:
        z = re.match('.*\.(.*)\.(.*)$', dom)
        return "%s_%s_%s" % (z.group(2),len(z.group(1)), len(dom))
    except:
        pass

    try:
        z = re.match('(.*)\.(.*)$', dom)
        return "%s_%s_%s" % (z.group(2),len(z.group(1)), len(dom))
    except:
        pass
    return "undefined_%s_%s" % (len(dom), len(dom))

def analyse_by_rdom(dom):
    hosts = r.keys("*;%s"%dom) # c class
    for i in hosts:
        rez = re.search("(.*);(.*)", i)
        graph_set.add("\"%s\" -> \"%s\";" % (rez.group(1), rez.group(2)))
        #clu = cal_cluster(rez.group(2))
        #print "\"%s\" -> \"%s\";" % (clu, rez.group(2))

def analyse_by_ip(ip):
    m = re.match('(\d+\.\d+\.\d+\.)', ip) # get c-class segment
    hosts = []
    hosts = r.keys("%s*;*"%m.group(1)) # c class
    for i in hosts:
        rez = re.search("(.*);(.*)", i)
        graph_set.add("\"%s\" -> \"%s\";" % (rez.group(1), rez.group(2)))
        analyse_by_rdom(rez.group(2))
        #clu = cal_cluster(rez.group(2))
        #print "\"%s\" -> \"%s\";" % (clu, rez.group(2))

def analyse_dom(clu):
    cdoms = r.keys("%s:*" % clu)
    for dz in cdoms:
        if re.search(':0$',  dz): # look for successeful queries
            rez = r.hmget(dz, "query", "firstseen", "lastseen", "count")
            query = json.loads(rez[0])
            if len(query["query"]) > 0 and len(query["response"]) > 0:
                graph_set.add("\"%s\" -> \"%s\";" %(query["query"][0], query["response"][0])) # assume all packets had one IP
                analyse_by_ip(query["response"][0])

doms = r.keys(domain_pattern)
rev = r.keys(reverse_pattern)
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
        #print "Processing cluster %s" % cl
    for dom in cluster_doms[cl]:
        graph_set.add("\"%s\" -> \"%s\";"  % (dom, cl))
    analyse_dom(dom)

for b in rev:
    d = re.search('(.*);(.*)', b)
    ip = d.group(1)
    dom = d.group(2)
    graph_set.add("\"%s\" -> \"%s\";" % (ip, dom))
    analyse_by_ip(ip)



for i in graph_set:
    print i

print "}"
