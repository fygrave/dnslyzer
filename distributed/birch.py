#!/usr/bin/env python

import random

import redis
from datetime import datetime
from math import sqrt
from operator import add

# FEATURES
# - This is a quick test implementation of the BIRCH algorithm (http://www.cs.sfu.ca/cc/459/han/papers/zhang96.pdf)
# - There's no guarantee that this implements the algorithm correctly.
# - It was never meant to be used in production environments.
# - We used it to study how the algorithm reacts to different (smallish) datasets and how to tweak its parameters.
# - It does not rebuild the tree if it hits a memory boundary
# - Because of that it works with a fixed T, there is no heuristic for T_(i+1)
# - Hence, it does not consider outliers because there's no tree rebuilding
# - Overall, it actually is not the whole algorithm, skips phase 2 to 4!


### SETTINGS
B = 10       # limit the amount of children a node can have
            # (the paper has another one especially for leaves. But we'll leave it at that!)

T = 5000     # maximum size (treshold) of a cluster before it has to be split


### SAMPLE EXECUTION SETTINGS
sample_dimensions = 10                  # how many dimensions does our tree have

sample_vectors_fillpercentage = 50      # to which percentage are the vectors filled.
                                        # at 50% and 10 dimensions our vectors will
                                        # on average have a value in 5 dimensions
                                        # this simulates sparse vectors

num_sample_points = 100                # how many vectors to insert



# keep a few statistics
splitcount = 0
nodecount = 0
entrycount = 0
leafcount = 0

class BaseNode(object):
    def __init__(self):
        global nodecount
        nodecount += 1

        self.n = 0
        self.ls = Vector()
        self.squared = 0

        self.parent = None

    @property
    def is_root(self):
        return not self.parent

    @property
    def level(self):
        count = 0
        r = self.parent
        while r:
            r = r.parent
            count +=1
        return count

    def indent(self):
        indent = '\n'
        r = self.parent
        while r:
            r = r.parent
            indent += '       '
        return indent

    @classmethod
    def closest(cls,node,list,force=False):
        "Returns the closest match of node to list"
        min_dist    = 0
        min_item    = None

        for item in list:
            dist = item.distance(node)
            #if not force:
            #    print "d:",dist,len(node),len(list)

            if not min_item:
                min_item = item
                min_dist = dist
            elif dist < min_dist:
                min_dist = dist
                min_item = item

        return min_item

    def d0(self,other):
        res = 0.0
        for key,val in self.ls.items():
            if key in other.ls:
                res += (val/self.n - other.ls[key]/other.n) ** 2
            else:
                res += (val/self.n) ** 2
        for key,val in other.ls.items():
            if key not in self.ls:
                res += (val/other.n) ** 2
        return res

    def d2(self,other):
        #print "\n\nself%s %s\nn: %i other n: %i" % (hash(self), self, self.n,other.n)
        return (other.n * self.squared + self.n * other.squared - 2 * (self.ls % other.ls)) / (self.n * other.n)

    def d4(self,other):
        dot1,dot2,dot3 = 0.0,0.0,0.0
        for val in self.ls.values():
            dot1 += (val/self.n) ** 2
        for val in other.ls.values():
            dot2 += (val/other.n) ** 2

        for key,val in self.ls.items():
            if key in other.ls:
                dot3 += ((val + other.ls[key]) / (self.n+other.n)) ** 2
            else:
                dot3 += (val / (self.n+other.n)) ** 2
        for key,val in other.ls.items():
            if key not in self.ls:
                dot3 += (val / (self.n+other.n)) ** 2

        return self.n*dot1 + other.n*dot2 - (self.n+other.n)*dot3

    distance = d2

    @classmethod
    def farthest_pair(cls,list):

        max_dist = None
        max_pair = None
        for e1 in list:
            for e2 in list:
                if e1==e2: continue

                dist = e1.distance(e2)
                if not max_pair:
                    max_pair = (e1,e2,)
                    max_dist = dist
                elif dist > max_dist:
                    max_pair = (e1,e2,)
                    max_dist = dist
        return max_pair

    @classmethod
    def closest_pair(cls,list):
        min_dist = None
        min_pair = None
        for e1 in list:
            for e2 in list:
                if e1==e2: continue

                dist = e1.distance(e2)
                if not min_pair:
                    min_pair = (e1,e2,)
                    min_dist = dist
                elif dist < min_dist:
                    min_pair = (e1,e2,)
                    min_dist = dist
        return min_dist

    def reset_cf(self):
        self.n = 0
        self.ls = Vector()
        self.squared = 0

    def update_cf(self,data):
        self.n += data.n
        self.ls += data.ls
        self.squared += data.squared

    @classmethod
    def calculate_height(self,list):
        if not list:
            return 1
        else:
            cum = 0
            for x in list:
                cum += x.height
            return cum

    @classmethod
    def calculate_depth(self,list):
        if not list:
            return 0
        else:
            return max([(lambda x:x.depth)(x) for x in list])



class Node(BaseNode):
    # has children which are nodes or leafs

    def __init__(self,*args,**kwargs):
        self.children = []
        super(Node,self).__init__(*args,**kwargs)
        global nodecount
        nodecount += 1

    @property
    def childnodes(self):
        return self.children

    @property
    def height(self):
        return self.calculate_height(self.children)

    @property
    def depth(self):
        return self.calculate_depth(self.children)

    def __str__(self):
        return '%sNODE %i (%i)->' % (self.indent(),hash(self),len(self.children)) + ' '.join([str(c) for c in self.children])

    def trickle(self,vector):
        "Gets a vector and hands it down to the closest child, checks for split afterwards"

        # refresh CF vector
        self.update_cf(vector)

        closest = self.closest(vector,self.children)

        if closest:
            closest.trickle(vector)
        else:
            l = Leaf()
            l.trickle(vector)
            self.add_node(l)

    def add_node(self,node,update=False):
        self.children.append(node)
        node.parent = self

        if update:
            self.update_cf(node)

        if len(self.children) > B:
            self.split_node()

    def split_node(self):
        global splitcount
        splitcount += 1

        c1,c2 = self.farthest_pair(self.children)

        # save the old list
        self.reset_cf()
        old_children = self.children
        self.children = []

        old_children.remove(c1)
        old_children.remove(c2)

        # two new leafs
        if self.is_root:
            node1 = Node()
        else:
            node1 = self
        node2 = Node()

        # add the farthest children to the new nodes
        node1.add_node(c1,True)
        node2.add_node(c2,True)

        while old_children:
            c = old_children.pop()
            if node1.distance(c) > node2.distance(c):
                node2.add_node(c,True)
            else:
                node1.add_node(c,True)

        # try to push down nodes if it only has one child...
        if len(node1.children) == 1:
            node1 = node1.children[0]
        if len(node2.children) == 1:
            node2 = node2.children[0]

        # create a new leaf and append it to our parent
        if self.is_root:
            self.add_node(node1,True)
            self.add_node(node2,True)
            # try to re-merge node 1 or 2
        else:
            self.parent.add_node(node2)

class Leaf(BaseNode):
    # has entries

    def __init__(self,*args,**kwargs):
        self.entries = []
        super(Leaf,self).__init__(*args,**kwargs)
        global leafcount
        leafcount += 1

    @property
    def childnodes(self):
        return self.entries

    @property
    def height(self):
        return self.calculate_height(self.entries)

    @property
    def depth(self):
        return self.calculate_depth(self.entries)

    def __str__(self):
        return '%sLEAF %i (%i)->' % (self.indent(),hash(self),len(self.entries)) + ' '.join([str(c) for c in self.entries])

    def trickle(self,vector):
        "Gets a vector and stores it in the closest entry, checks for split afterwards"

        closest = self.closest(vector,self.entries)

        if closest:
            closest.store_vector(vector)
            self.update_cf(vector)
        else:
            e = Entry()
            e.store_vector(vector)
            self.add_entry(e)


    @classmethod
    def closest(cls,node,list,force=False):
        "Returns the closest match of node to list"
        min_dist    = 0
        min_item    = None

        if not list:
            return

        for item in list:
            dist = item.distance(node)
            #if not force:
            #    print "d:",dist,len(node),len(list)

            if not min_item:
                min_item = item
                min_dist = dist
            elif dist < min_dist:
                min_dist = dist
                min_item = item

        # try to insert into min_item and check T afterwards
        if min_item.test_radius(node) > T:
            return

        return min_item


    def add_entry(self,entry):
        self.entries.append(entry)
        entry.parent = self

        self.update_cf(entry)
        if len(self.entries) > B:
            self.split_leaf()

    def split_leaf(self):
        global splitcount
        splitcount += 1

        e1,e2 = self.farthest_pair(self.entries)

        # save the old list
        self.reset_cf()
        old_entries = self.entries
        self.entries = []

        old_entries.remove(e1)
        old_entries.remove(e2)

        # two new leafs
        leaf1 = self
        leaf2 = Leaf()
        leaf1.add_entry(e1)
        leaf2.add_entry(e2)

        while old_entries:
            e = old_entries.pop()
            if leaf1.distance(e) > leaf2.distance(e):
                leaf2.add_entry(e)
            else:
                leaf1.add_entry(e)


        # create a new leaf and append it to our parent
        self.parent.add_node(leaf2)


class Entry(BaseNode):
    # has vectors
    is_entry = True

    def __str__(self):
        #s = ''
        #for v in self.vectors:
        #    s = "%s %s"%(s, v.domain)
        return "Entry : %s (%i total)" % (self.vectors[0].domain, len(self.vectors))

    def __init__(self,*args,**kwargs):
        self.vectors = []
        super(Entry,self).__init__(*args,**kwargs)
        global entrycount
        entrycount += 1
        self.radius = 0.0

    def testvolume(self,vector=None):
        if not self.vectors:
            return 0
        vecs = self.vectors[:]

        if vector:
            vecs.append(vector)

        n = len(vecs)

        dist = 0
        for v1 in vecs:
            for v2 in vecs:
                dist += v1.distance(v2)

        vol = (dist/(n*(n-1))) ** 0.5

        #print "vol:",vol
        return vol
    volume = property(testvolume)

    def test_radius(self,vector):
        if self.n == 0:
            return 0

        new_n = self.n + 1
        new_ls = self.ls + vector.ls
        new_squared = self.squared + vector.squared

        testrad = self.radius + ((new_ls / new_n).distance(vector))
        #print "testrad:",testrad
        return testrad

    @property
    def volume(self):
        return self.radius

    @property
    def refdist(self):
        dist = 0
        for v1 in self.vectors:
            for v2 in self.vectors:
                dist += v1.distance(v2)
        return dist

    @property
    def height(self):
        return len(self.vectors)

    @property
    def depth(self):
        return 1

    def store_vector(self,vector):
        "Stores a point in its list, this is the end!"
        self.vectors.append(vector)
        self.update_cf(vector)
        self.radius += (self.ls / self.n).distance(vector)


class Vector(dict):
    n = 1
    domain = ''
    def __init__(self,*args,**kwargs):
        self._squared = None
        self.ls = self
        super(Vector,self).__init__(*args,**kwargs)

    def __hash__(self):
        assert self.item,"Cannot hash a value without its item"
        return hash(self.item)

    def __add__(self,other):
        output = {}
        for key,val in self.items():
            if key in other:
                output[key] = val + other[key]
            else:
                output[key] = val

        for key,val in other.items():
            if key not in self:
                output[key] = val

        return Vector(output)

    def __sub__(self,other):
        output = {}
        for key,val in self.items():
            if key in other:
                output[key] = val - other[key]
            else:
                output[key] = val

        for key,val in other.items():
            if key not in self:
                output[key] = -val

        return Vector(output)

    def __div__(self,scalar):
        #print "div:",scalar
        output = {}
        #python divisions..
        scalar = float(scalar)
        for key,val in self.items():
            output[key] = val / scalar
        return Vector(output)

    def __mod__(self,other):
        "Dot Product"
        result = 0.0
        for key,val in self.items():
            if key in other:
                result += val * other[key]
        return result

    def __pow__(self,p):
        output = {}
        for key,val in self.items():
            output[key] = val ** p
        return Vector(output)

    def sqrt(self):
        output = {}
        for key,val in self.items():
            output[key] = sqrt(val)
        return Vector(output)

    def length(self):
        length = 0
        for val in self.values():
            length += val**2
        return sqrt(length)

    @property
    def squared(self):
        if not self._squared:
            self._squared = self % self
        return self._squared

    def distance(self,other):
        distance = 0
        num = 0
        matching = []
        for key,val in self.items():
            num += 1
            if key in other:
                matching.append(key)
                distance += (val - other[key]) ** 2
            else:
                distance += val ** 2

        for key,val in other.items():
            if key not in self:
                num += 1
                distance += val ** 2

        return sqrt(distance)


if __name__ == '__main__':

    # SMALL 2D SAMPLE (takes ~ 2 seconds on a Intel Core2 Duo 2.5GHz):
    print "start clustering"
    B = 10
    T = 35
    sample_dimensions = 2
    sample_vectors_fillpercentage = 100
    num_sample_points = 10000

    vectors = []

    # we'll produce random sample points
    # note that these points really are sparse vectors!
    # we're adding random values to random dimensions
    # so in the end only a few dimensions will have values!
    r = redis.Redis('localhost')
    d = r.keys("*cc_14*:3")
    for item in d:
        v = Vector()
        v.domain = item
        count = 0
        for c in item:
            v[count] = ord(c)
            count = count + 1
        vectors.append(v)

    # let's measure the computing time
    start = datetime.now()
    print "starting clustering... %i domains" % len(vectors)

    # build the first node - it's our root
    root = Node()

    # insert vector after vector
    for v in vectors:
        # insert this vector to the tree's root
        root.trickle(v)

    print root
    time = datetime.now()-start
    print "took %s (%.2fms per point)" % (time,(time.seconds*1000+time.microseconds/1000.0)/num_sample_points)
