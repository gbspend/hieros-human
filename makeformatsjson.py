import json, formats, formatssw
import wordbags as wb
from random import shuffle

def cleanrec(node):
	if 'parent' in node:
		del node['parent']
	
	r = node['replace']
	if r:
		node['replace'] = (r['word'],r['pos'])
	
	for c in node['children']:
		cleanrec(c)

def prepform(format):
	root = format['root']
	choices = [w for w in wb.getAll(root['pos']) if ' ' not in w]
	shuffle(choices)
	format['rootchoices'] = choices[:30]
	cleanrec(root)

fs = formats.makeAllRawForms()
for f in fs:
	prepform(f)

fsws = formatssw.makeAllRawForms()
for f in fsws:
	prepform(f)

with open('formats.json','w') as outf:
	json.dump(fs,outf)

with open('formatssw.json','w') as outf:
	json.dump(fsws,outf)
