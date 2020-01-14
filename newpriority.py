import helpers as h
import random
import heapq as hq

numChildren = 4
strikes = 3
maxSpecies = 10

class Species:
	def __init__(self,s,node):
		self.seed = s
		self.isDead = False
		self.heap = []
		self.stale = 0
		self.lowsc = node.score
		self.bestsc = node.score
		self.bestch = node
		self.secondch = None
		self.push(node)

	def checkBest(self,curr):
		if curr.score < self.lowsc:
			self.lowsc = curr.score
		if curr.score > self.bestsc:
			self.bestsc = curr.score
			self.secondch = self.bestch
			self.bestch = curr
			self.stale = 0
			return True
		return False

	def push(self,node):
		if self.stale > strikes:
			return
		if not self.heap:
			self.isDead = False
		hq.heappush(self.heap,(-node.score,node))

	def step(self):
		if self.isDead:
			return []
		if not self.heap:
			self.isDead = True
			return []
		curr = hq.heappop(self.heap)[1]
		if not self.checkBest(curr):
			self.stale += 1
			if self.stale > strikes:
				self.isDead = True
				return []
		childs = []
		for i in xrange(numChildren):
			newch = curr.getChild()
			if newch is not None:
				childs.append(newch)
		return childs


class Settings:
	#rf is function that takes a "locks" list (see "formats" functions in micro.py)
	#canR is list of indices that can be regenerated
	def __init__(self,rf,canR):
		self.regen = rf
		self.canRegen = canR

class Node:
	#s is string (artifact)
	#sett is Settings object
	def __init__(self,s,sett):
		self.s = s
		self.sett = sett
		self.isbad = False
		try: # fixes unicode characters trying to sneak through; see https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string
			self.words = h.strip(s).split()
		except Exception as e:
			#print s, e
			self.isbad = True
		self.score = None#sett.calcScore
		#print "--Created node [",s,"]",self.score

	def getChild(self):
		i = random.choice(self.sett.canRegen)
		lock = self.words[:]
		lock[i] = None
		temp = self.sett.regen(lock)
		if not temp:
			return None
		news,fraw = temp
		if not news:
			return None
		child = Node(news,self.sett)
		if child.isbad:
			return None

		#TODO! This rejects too many, I think? Test more! Maybe make it not match the original story...?
		#if h.numMatch(self.words,child.words) > 2: #too similar
		#	print self.words,child.words
		#	return None
		return child
		
def getIndex(story, i):
	return h.strip(story.split(' ')[i])

#stories can be a string or list
#NOT STRIPPED
def best(stories,regenf,canRegen,scoref,fraw,norm=False):
	if type(stories) != list:
		stories = [stories]
	species = {}
	seedi = fraw['root']['index']
	
	bad = True
	for s in stories:
		if not s:
			continue
		seed = getIndex(s,seedi)
		root = Node(s,Settings(regenf,canRegen))
		if root.isbad:
			break
		root.score = scoref([s])[0]
		species[seed] = Species(seed,root)
		bad = False
	if bad:
		print "Refiner got no stories!"
		return None
		
	while True:
		#print "--------------------------------"
		children = []
		allDead = True
		for k in sorted(species.keys(),key=lambda x: species[x].bestsc,reverse=True)[:maxSpecies]:
			p = species[k]
			if not p.isDead:
				allDead = False
				children += p.step()
		if allDead and not children:
			break
		if not children:
			continue
		#print "Num species, children:",len(species.keys()),",",len(children)
		#raw = [h.strip(c.s) for c in children]
		scores = scoref([c.s for c in children])
		for i,child in enumerate(children):
			child.score = scores[i]
			k = getIndex(child.s,seedi)
			if k not in species:
				ni2 = Species(k,child)
				species[k] = ni2
			else:
				species[k].push(child)
		#print len(species)
	
	lowest = 1000
	highest = -1000
	choices = []
	for k in species:
		p = species[k]
		if p.lowsc < lowest:
			lowest = p.lowsc
		if p.bestsc > highest:
			highest = p.bestsc
		#print p.bestch.s,p.bestsc
		assert p.bestch.score == p.bestsc
		choices.append((p.bestch.s, p.bestsc))
		if p.secondch: #balance between not letting good stories getting buried under slightly better stories and minimizing species score bias
			choices.append((p.secondch.s,p.secondch.score))
	
	if norm:
		choices = [(s,h.rangify(c,lowest,highest,0,1)) for s,c in choices]
	
	choices = sorted(choices,key=lambda x: x[1],reverse=True)[:maxSpecies]
	if False:
		for s,c in choices:
			print s,c
	m = min([c[1] for c in choices])
	if m >=0:
		m = 0
	i = h.weighted_choice(choices,-m)
	return choices[i] + (choices,)
