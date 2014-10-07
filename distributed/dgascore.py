#!/usr/bin/env python
import math
import pickle
import os.path
import os
import re
import sys
import json
import numpy
import numpy as np

class DGAScore:
  NSIZ = 5
  NGRAMS_FILE = './ngrams.pickle'
  def __init__(self):
    self.ngrams_chain = {}
    self.ngrams =[]
    for n in range(0,self.NSIZ):
      self.ngrams.append([])

    if os.path.isfile(self.NGRAMS_FILE):
      data = pickle.load(open(self.NGRAMS_FILE, "rb"))
      self.ngrams_chain = data[0]
      self.ngrams = data[1]
    else:
      self.build_ngrams()
      data = []
      data.append(self.ngrams_chain)
      data.append(self.ngrams)
      #print json.dumps(data)
      pickle.dump(data, open(self.NGRAMS_FILE, 'wb'))


  def build_ngrams(self):
    f = open('alexa-1m.txt')
    for line in f.readlines():
      line = line.rstrip('\n')
      if line[len(line)-1] != '.':
        line = "%s." % line
      #print line
      self.add_training_string(line)
      self.normalize_ngrams_chain()


  def update_ngram_chain(self, n, str):
    if not self.ngrams_chain.has_key(n):
      self.ngrams_chain[n] = {}
    for i in range(0, len(str) - n):
      ngram1 = str[i:i + n]
      #print n
      #print "len: %i" % len(self.ngrams[n])
      #print "ngram: %s" % ngram1
      try:
        #print "Array offset %i" % self.ngrams_chain[n][ngram1]
        self.ngrams[n][self.ngrams_chain[n][ngram1]] +=1.0
      except KeyError:
        self.ngrams_chain[n][ngram1]= len(self.ngrams[n])
        self.ngrams[n] = np.append(self.ngrams[n], [0.0])



  def normalize_ngram_chain(self, n):
    total = float(len( self.ngrams[n]))
    #map(lambda key: self.ngrams_chain[n][key] = float(self.ngrams_chain[n][key]/total), self.ngrams_chain[n].keys())
    self.ngrams[n] = np.divide(self.ngrams[n], total)
    #ngram_chain = self.ngrams_chain[n]
    #for key in ngram_chain.keys():
    #  ngram_chain[key] = ngram_chain[key]/total
    #self.ngrams_chain[n] = ngram_chain



  def normalize_ngrams_chain(self):
      map(self.normalize_ngram_chain, self.ngrams_chain.keys())




  def add_training_string(self, str):
    str = str.lower()

    for n in range(1, self.NSIZ):
      self.update_ngram_chain(n, str)


  def dump(self):
    print self.ngrams_chain


  def score_for_ngram(self, n, str):
    if len(str) < n:
      return 0.0
    sum = 0.0

    for i in range(0, len(str) - n):
      ngram1 = str[i:i+ n]

      p = -1.0
      try:
        p = self.ngrams[n][self.ngrams_chain[n][ngram1]]
      except KeyError:
        pass
      sum = sum + p
    return (sum / float(len(str) - n + 1))


  def perplexity_for_string(self, str):
    str = re.sub(r'^(www|imap|mail|mx|smtp|ns)', '', str)
    ns_first = 1
    ns_last =  2
    if len(str) < ns_last:
      return 0.0

    sum = 0.0
    for i in range(0, len(str) - ns_last):
      ngram1 = str[i:i+ ns_last]
      p_w2_w1 = 1.0
      if self.ngrams_chain[ns_last].has_key(ngram1):
        p_w2_w1 = self.ngrams[ns_last][self.ngrams_chain[ns_last][ngram1]]
      for n in reversed(range(ns_first, ns_last)):
        ngram1 = str[i:n]
        p_w2_w1 = 1.0
        if self.ngrams_chain[n].has_key(ngram1):
          p_w2_w1 = self.ngrams[n][self.ngrams_chain[n][ngram1]]
      sum = sum + math.log(p_w2_w1)
    perp = math.exp(sum * -1/(len(str) - ns_last + 1))
    return perp


  def score_for_string(self, str):
    total_weight = 0.0
    sum = 0.0
    for n in range(1, self.NSIZ):
      weight = n
      total_weight = weight + total_weight
      sum = sum + float(self.score_for_ngram(n, str)) * weight
    sum = sum / total_weight
    sum = sum * -1000.0
    sum = max(0.0, sum)
    return sum

if __name__ == "__main__":
  dgascore = DGAScore()

  for line in open(sys.argv[1]).readlines():
    line = line.rstrip('\n')
    if line[len(line) - 1] != '.':
      line = "%s." % line
      score = dgascore.score_for_string(line)
      perp = dgascore.perplexity_for_string(line)

      print "%s score: %f perp: %s" % (line, score, perp)
