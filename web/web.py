#!/usr/bin/env python

from bottle import route, run, debug, template,static_file,request
import json
import bottle
import bottle.ext.redis
import ConfigParser as CFG
import time
import argparse

app = bottle.Bottle()
plugin = bottle.ext.redis.RedisPlugin(host='localhost')
app.install(plugin)



@app.route('/api/v1/lookup/last', method="GET")
@app.route('/api/v1/lookup/last', method="POST") 
def get_last(rdb):
    keys = rdb.keys("h:*")
    data = []
    for k in keys:
        try:
            dom = json.loads(rdb.get(k))
            rdb.delete(k)
            data.append(dom)
        except Exception, e:
            print e
    return json.dumps(data)




@app.route('/api/v1/lookup/clusters', method="POST")
@app.route('/api/v1/lookup/clusters', method="GET")
def get_clusters(rdb):
    keys = rdb.keys("c:*")
    data = {}
    for k in keys:
        try:
            dom = list(rdb.smembers(k))
            data[k]=dom
        except Exception, e:
            print e
    return json.dumps(data)


parser = argparse.ArgumentParser(description='PDNS RESTful API')
parser.add_argument('config', type=file, help= 'config file')
parser.set_defaults(config = "http.cfg")
r = parser.parse_args()
print r.config


config = CFG.ConfigParser()
config.readfp(r.config)


HOST_NAME=config.get("main", "host")
PORT_NUMBER=int(config.get("main", "port"))
app.run(host=HOST_NAME, port=PORT_NUMBER, debug=True)
