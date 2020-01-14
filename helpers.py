from collections import defaultdict
from nltk.corpus import wordnet as wn
import string
import numpy as np
import random
from pattern.en import parse, pluralize, comparative, superlative, conjugate, PRESENT, PAST, PARTICIPLE, INFINITIVE

#maps number n, which is in rage oldmin--oldmax to newmin--newmax
def rangify(n,oldmin,oldmax,newmin,newmax):
	R = float(newmax - newmin) / (oldmax - oldmin)
	return (n - oldmin) * R + newmin

def baseWord(word):
	base = wn.morphy(word)
	if base is None:
		return word
	return base

def strip(s):
	return str(s).translate(None, string.punctuation).lower().strip()

def firstCharUp(s):
	return s[0].upper() + s[1:]

def new_total_similarity(word, relations, w2v):
	if word not in w2v:
		return 0.0
	return sum((max(0.0,get_cosine_similarity(word, x, w2v)) for x in relations if x in w2v), 0.0)

def get_cosine_similarity(word1, word2, w2v):
	vec1 = w2v.get_vector(word1)
	vec2 = w2v.get_vector(word2)
	dividend = np.dot(vec1, vec2)
	divisor = np.linalg.norm(vec1) * np.linalg.norm(vec2)
	result = dividend / divisor
	return result

def w2vsortlistNew(l,words,w2v):
	return sorted(l,reverse=True,key=lambda x: new_total_similarity(x,words,w2v))

def strip_tag(w):
	loc = w.find('_')
	if loc == -1:
		return w
	return w[:-(len(w)-loc)]

#choices is a list of (choice,weight) tuples
#Doesn't need to be sorted! :D
#returns index
def weighted_choice(choices,offset=0):
	total = sum(w+offset for c, w in choices)
	r = random.uniform(0, total)
	upto = 0
	for i,t in enumerate(choices):
		w = t[1]+offset
		if upto + w >= r:
			return i
		upto += w
	assert False, "Shouldn't get here"

#start: POS tagged word like "dog_NN"
#relations: list of tuples/lists of len 2, untagged [(cat, meow), (cow, moo)]
#tag1: POS tag of left hand of relations (t[0]) and start
#tag2: POS tag of right hand of relations (t[1])
# Scholar by Daniel Ricks: https://github.com/danielricks/scholar
def get_scholar_rels(start, relations, w2v, tag1, tag2,num=10):
	counts = defaultdict(float)
	ret = []
	for rel in relations:
		positives = [rel[1] + tag2, start]
		negatives = [rel[0] + tag1]
		flag = False
		for w in positives+negatives:
			if w not in w2v:
				flag = True
				break
		if flag:
			continue

		idxs, metrics = w2v.analogy(pos=positives, neg=negatives, n=num)
		res = w2v.generate_response(idxs, metrics).tolist()
		ret += res
		for x in res:
			counts[x[0]] += x[1]

	ret = [x[0] for x in ret]
	ret = sorted(ret, key=counts.get, reverse=True)
	ret = [x[:-(len(x)-x.find('_'))] for x in ret]
	ret = list(set(ret)) # remove duplicates (and undoes sort!)

	return ret

#good/bad are axis ends
#l is list of sentences to score
#p is Penseur instance
#returns score, higher is better
#len(l) > 1
def getSkipScores(bad,good1,good2,sts,p):
	story_list = sts[:]
	story_list += ['asdf'] #need to add/remove dummy story in case len(story_list) ==1
	p.encode([strip(s) for s in story_list])
	scores = p.get_axis_scores(bad,good1,good2)
	#story_list = story_list[:-1]
	scores = scores[:-1]
	#for i,story in enumerate(story_list):
	#	writeCsv("basic1D",[story,scores[i]])
	return scores

def addToDictList(d,k,v):
	if k not in d:
		d[k] = []
	d[k].append(v)

def getPOS(w):
	return parse(w).split('/')[1].split('-')[0]

def numMatch(parentWords,childWords):
	ret = 0
	for i in range(len(parentWords)):
		if parentWords[i] == childWords[i] or wn.morphy(parentWords[i]) == wn.morphy(childWords[i]):
			ret += 1
	return ret

'''
* is pattern.en
^ is custom
= is leave it
# is can't
JJR <- JJ comparative
JJS <- JJ superlative
NNS <- NN pluralize
NNP <- NN=
NNPS <- NN, NNP pluralize (both)
PDT <- DT#
PRP <- RP#
PRP$ <- PRP^ RP#
RBR <- RB comparative
RBS <- RB superlative
VBD <- VB conjugate
VBG <- VB conjugate?
VBN <- VB conjugate?
VBP <- VB conjugate
VBZ <- VB conjugate
WDT <- DT#
WP$ <- WP^
WRB <- RB#
'''

PRPD = {'me':'mine','you':'yours','he':'his','she':'hers','it':'its','us':'ours','them':'theirs'}
WPD = {'who':'whose'}

#try to conjugate the word from POS p to POS target
#See "p in target" cases above
def tryPOS(word,p,target):
	if target in p and target not in ['RB','DT','RP']:
		if target == 'PRP' or target == 'WP':
			d = WPD
			if target == 'PRP':
				d = PRPD
			for k in d:
				if d[k] == word:
					return k
			return None
		return wn.morphy(word)

	#else
	if target == 'PRP$' and p == 'PRP':
		return PRPD.get(word)
	if target == 'WP$':
		return WPD.get(word)
	if p == 'NN':
		if target == 'NNP':
			return word
		else:
			return pluralize(word)
	if p == 'NNP':
		return pluralize(word)
	if 'VB' in p:
		t = ''
		if target == 'VBD':
			t = PAST
		if target == 'VBP':
			t = INFINITIVE
		if target == 'VBZ':
			t = PRESENT
		if target == 'VBN':
			t = PAST+PARTICIPLE
		if target == 'VBG':
			t = PARTICIPLE
		if t:
			return conjugate(word,tense=t)
	
	ret = ''
	if target == 'JJR' or target == 'RBR':
		ret = comparative(word)
	if target == 'JJS' or target == 'RBS':
		ret = superlative(word)
	if not ret or ' ' in ret:
		return None #default
	else:
		return ret

