import formatssw
import helpers as h
from itertools import chain, izip_longest
from random import choice
import wordbags as wb

def analogy(word,start,startTag,end,endTag):
	print "%s (%s) : %s (%s) :: %s (%s) : _______ (%s)" % (start, startTag, end, endTag, word, startTag, endTag)
	word = raw_input()
	return word

def plugin(plug,words):
	parts = plug.split('W')
	return ''.join([x for x in list(chain.from_iterable(izip_longest(parts, words))) if x is not None])

#replace with human API call?
def genRoot(root):
	pos = root['pos']
	return choice(wb.getAll(pos))

def genrec(node,parent,prev,lock):
	if not parent: #root
		newword = lock[node['index']]
		assert newword
	else:
		i = node['index']
		if parent['replace']:
			parent = parent['replace']
		nodePos = node['pos']
		newword = analogy(prev,parent['word'],parent['pos'],node['word'],nodePos)
		lock[i] = newword
	for child in node['children']:
		genrec(child,node,newword,lock)

def doit(format):
	root = format['root']
	lock = [None,None,None,None,None,None]
	if lock[root['index']] is None:
		new_root = genRoot(root)
		if not new_root:
			return None
		lock[root['index']] = new_root
	genrec(root,None,None,lock)
	for i in format['cap']:
		lock[i] = h.firstCharUp(lock[i])
	return plugin(format['plug'],lock)

if __name__ == '__main__':
	formats = formatssw.makeAllRawForms()
	format = choice(formats)
	print doit(format)

'''
First two trials; pretty good!

change (VB) : progress (NN) :: apportion (VB) : _______ (NN)
funds
progress (NN) : personal (JJ) :: funds (NN) : _______ (JJ)
monetary
change (VB) : can (MD) :: apportion (VB) : _______ (MD)
might
change (VB) : world (NN) :: apportion (VB) : _______ (NN)
income
world (NN) : the (DT) :: income (NN) : _______ (DT)
some
Monetary funds might apportion some income.

friend (NN) : one (CD) :: review (NN) : _______ (CD)
a
friend (NN) : faces (NNS) :: review (NN) : _______ (NNS)
words
faces (NNS) : two (CD) :: words (NNS) : _______ (CD)
three
friend (NN) : school (NN) :: review (NN) : _______ (NN)
magazine
school (NN) : high (JJ) :: magazine (NN) : _______ (JJ)
tredny
A review, three words. Tredny magazine.
'''
