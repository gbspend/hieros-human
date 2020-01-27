import pickle, formats, formatssw

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
	cleanrec(root)

fs = formats.makeAllRawForms()
for f in fs:
	prepform(f)

fsws = formatssw.makeAllRawForms()
for f in fsws:
	prepform(f)

with open('formats.p','w') as outf:
	pickle.dump(fs,outf)

with open('formatssw.p','w') as outf:
	pickle.dump(fsws,outf)
