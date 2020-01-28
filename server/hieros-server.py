from flask import Flask, jsonify, abort, make_response, request, g
import sqlite3
import pickle
import string
from random import randint
from itertools import chain, zip_longest

app = Flask(__name__)

DATABASE = 'hieros.db'

#with open("formats.p") as f:
with open("formatssw.p","rb") as f:
	formats = pickle.load(f)

#stores which stories are being worked on / scored
working = set()

#https://docs.python.org/2/library/sqlite3.html
def get_db():
	if 'db' not in g:
		g.db = sqlite3.connect(DATABASE)
	return g.db

def query_db(query, args=(), one=False):
	cur = get_db().cursor()
	cur.execute(query, args)
	rv = cur.fetchall()
	return (rv[0] if rv else None) if one else rv

def exec_db(query, args=()):
	db = get_db()
	c = db.cursor()
	c.execute(query, args)
	id = c.lastrowid
	db.commit() #if it's slow, maybe move this to teardown_appcontext instead?
	return id

#=====================

@app.teardown_appcontext
def close_connection(e):
	db = g.pop('db', None)
	if db is not None:
		db.close()

@app.errorhandler(404)
def not_found(error):
	return make_response(jsonify({'error':'Not found'}), 404)

#=====================

#finds given index in format tree, starting with "node" (root)
#now we don't have to store nodes in SQL :)
def findInd(node, i):
	if node['index'] == i:
		return node
	for c in node['children']:
		n = findInd(c,i)
		if n:
			return n
	return None

def pushHold(story_id, i, node_ind, prev_word, par_word, par_pos):
	exec_db("INSERT INTO holds(story_id, i, node_ind, prev_word, par_word, par_pos) VALUES (?, ?, ?, ?, ?, ?)", (story_id, i, node_ind, prev_word, par_word, par_pos))

def pushKids(story_id, parent, prev):
	pword = parent['word']
	ppos = parent['pos']
	repl = parent['replace']
	if repl:
		pword, ppos = repl
	
	#get next holds id
	holds = query_db("SELECT i FROM holds WHERE story_id=? ORDER BY i DESC", (story_id,))
	if not holds:
		i = 0
	else:
		i = holds[0][0]+1
	
	first = i
	for c in parent['children']:
		pushHold(story_id, i, c['index'], prev, pword, ppos)
		i += 1
	
	return first

#delete messed up story and all holds so that they don't gum up the works
#TODO also clean up queues?
def deleteStory(story_id):
	exec_db("DELETE FROM stories WHERE id=?",(story_id,))
	exec_db("DELETE FROM holds WHERE story_id=?",(story_id,))

punct_transl = str.maketrans('', '', string.punctuation)
def strip(s):
	return s.translate(punct_transl).lower().strip()

def getDescendants(node, des):
	for c in node['children']:
		des.add(c['index'])
		getDescendants(c, des)

def updateKids(story_id, parent, prev):	
	for c in parent['children']:
		exec_db("UPDATE holds SET prev_word=? WHERE story_id=? AND node_ind=?",(prev,story_id,c["index"]))

def firstCharUp(s):
	return s[0].upper() + s[1:]

def plugin(plug,words):
	parts = plug.split('W')
	return ''.join([x for x in list(chain.from_iterable(zip_longest(parts, words))) if x is not None])

def makeStory(form, lock):
	for i in form['cap']:
		lock[i] = firstCharUp(lock[i])
	return plugin(form['plug'],lock)

#https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
#=Root========

#return next root needed (will create new story)
@app.route('/hieros/api/root', methods=['GET'])
def get_root():
	i = randint(0,len(formats)-1)
	root = formats[i]['root']
	return jsonify({'i':i,'root_word':root['word'],'root_pos':root['pos']})

#receive root & create new story to work on
@app.route('/hieros/api/root', methods=['POST'])
def insert_root():
	if not request.json:
		abort(400,"no json in request")
	if 'i' not in request.json or 'word' not in request.json:
		abort(400,"i or word not in json:"+str(request.json.keys()))
	try:
		i = int(request.json['i'])
	except ValueError:
		abort(400,"json[i] not int:"+str(i))
	word = strip(request.json['word'])
	if not word or i >= len(formats):
		abort(400,"stripped json[word] empty:"+str(request.json['word']))

	f = formats[i]
	root = f['root']
	
	#create story entry
	args = [i,None,None,None,None,None,None,0]
	args[root['index']+1] = word#fill in root
	story_id = exec_db("INSERT INTO stories(form, word0, word1, word2, word3, word4, word5, hold_i) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", args)
	
	#fill in hold (skip root; it's already done, and it's never regen'd)
	first = pushKids(story_id,root,word)
	assert first == 0

	return make_response({},200)

#=Analogy=====

#return next analogy needed
@app.route('/hieros/api/analogy', methods=['GET'])
def get_analogy():
	stories = query_db("SELECT * FROM stories WHERE hold_i<5 ORDER BY id")
	if not stories or all(row[0] in working for row in stories):
		return make_response({},200) #nothing to work on (ask for something else)
	
	curr = [row for row in stories if row[0] not in working][0]
	story_id = curr[0]
	format = formats[curr[1]]
	locks = list(curr[2:8])
	hold_i = curr[8]
	working.add(story_id)
	
	holds = query_db("SELECT i,node_ind,prev_word,par_word,par_pos FROM holds WHERE story_id=? ORDER BY i", (story_id,))
	if not holds:
		#delete from stories so we don't get caught in a loop when we GET analogy again
		deleteStory(story_id)
		abort(400,"no matching holds to story_id:"+str(story_id))
	
	i,node_ind,prev_word,par_word,par_pos = holds[hold_i]
	if i != hold_i:
		deleteStory(story_id)
		abort(400,"story's hold_i doesn't match hold list's i:"+str(hold_i)+" "+str(i))
	
	root = format['root']
	node = findInd(root,node_ind)
	
	#if we're mutating, tell client to ask for a word other than not_word
	not_word = None
	curr_lock = locks[node['index']]
	if curr_lock is not None:
		not_word = curr_lock
	
	#query = pword+" ("+ppos+") : "+node['word']+" ("+npos+") :: "+prev+" ("+ppos+") : _______ ("+npos+")"
	#we'll sanity check that par_word/pos and node_word/pos match on the other side!
	return jsonify({'story_id':story_id, "par_word":par_word, "par_pos":par_pos, "node_word":node['word'], "node_pos":node['pos'], "prev_word":prev_word, "not_word":not_word})

#receive analogy
@app.route('/hieros/api/analogy', methods=['POST'])
def insert_analogy():
	if not request.json:
		abort(400,"no json in request")
	keys = ["new_word", "node_pos", "node_word",  "par_pos",  "par_word",  "prev_word",  "story_id"]
	if not all([k in request.json for k in keys]):
		abort(400,"missing keys from json:"+str(request.json.keys()))
	new_word = strip(request.json["new_word"])
	if not new_word:
		abort(400,"stripped request.json[new_word] is empty:"+str(request.json["new_word"]))
	node_pos = request.json["node_pos"]
	node_word = request.json["node_word"]
	par_pos = request.json["par_pos"]
	par_word = request.json["par_word"]
	prev_word = request.json["prev_word"]
	story_id = request.json["story_id"]
	
	stories = query_db("SELECT * FROM stories WHERE id=?",(story_id,))
	if not stories:
		deleteStory(story_id)
		abort(400,"no matching story to id:"+str(story_id))
	curr = stories[0]
	format = formats[curr[1]]
	root = format['root']
	locks = list(curr[2:8])
	hold_i = curr[8]
	mutating = curr[9] #mutating is HOLD index, not node index!
	if story_id in working:
		working.remove(story_id)
	else:
		pass #whatev?
	
	holds = query_db("SELECT * FROM holds WHERE story_id=? ORDER BY i",(story_id,))
	if not holds:
		deleteStory(story_id)
		abort(400,"no matching holds to story_id:"+str(story_id))
	dummy1,dummy2,i,node_ind,h_prev_word,h_par_word,h_par_pos = holds[hold_i]
	if i != hold_i:
		deleteStory(story_id)
		abort(400,"story's hold_i doesn't match hold list's i:"+str(hold_i)+" "+str(i))
	
	node = findInd(root,node_ind)
	#sanity check that par_word/pos and node_word/pos match on this side
	if prev_word != h_prev_word or par_word != h_par_word or par_pos != h_par_pos or node_word != node['word'] or node_pos != node['pos']:
		abort(400,"something in request doesn't match:"+prev_word+" "+ h_prev_word+" "+ par_word+" "+ h_par_word+" "+ par_pos+" "+ h_par_pos+" "+ node_word+" "+ node['word']+" "+ node_pos+" "+ node['pos'])
	
	#if we're mutating, the current hold's node's index should not be None in locks
	if mutating is not None:
		assert locks[node_ind] is not None
	
	#update locks and increment hold_i
	locks[node_ind] = new_word
	
	if mutating is not None:
		#don't just increment hold_i and pushkids, instead...
		#get descendant indexes of mutating (index)
		mut_node = findInd(root,holds[mutating][3]) #"mutating" is hold index; use it to get correct node index
		des = set() #out var
		getDescendants(mut_node, des)
		print("des:",des)
		#increment hold_i until either it's pointing at an index in des or hold_i == 5 :)
		while True:
			hold_i += 1
			if hold_i >= 5:
				break
			curr_ind = holds[hold_i][3]
			if curr_ind in des:
				break
		assert hold_i <=5
		#instead of pushing kids, update kids with new prev word
		updateKids(story_id,node,new_word)
	
	else:
		hold_i += 1
		first = pushKids(story_id,node,new_word)
		if not hold_i <= first:
			abort(400,"new hold i is greater that first pushed kid:"+str(hold_i)+" "+str(first))
	
	#update story with new lock and hold_i
		#don't have to do anything if it's done; GET analogy will ignore it and GET score will just pick it up :)
	args = locks + [hold_i, story_id]
	exec_db("UPDATE stories SET word0=?, word1=?, word2=?, word3=?, word4=?, word5=?, hold_i=? WHERE id=?", args)
	return make_response({},200)

#=Score=======

#return next score needed
@app.route('/hieros/api/score', methods=['GET'])
def get_score():
	stories = query_db("SELECT * FROM stories WHERE hold_i>=5 AND score IS NULL ORDER BY id")
	#we can reuse "working" for scoring too :)
	if not stories or all(row[0] in working for row in stories):
		return make_response({},200) #nothing to work on (ask for something else)
	curr = [row for row in stories if row[0] not in working][0]
	story_id = curr[0]
	format = formats[curr[1]]
	locks = list(curr[2:8])
	working.add(story_id)
	
	story = makeStory(format,locks)
	return jsonify({'story_id':story_id, "story":story})

#receive score
@app.route('/hieros/api/score', methods=['POST'])
def insert_score():
	if not request.json:
		abort(400,"no json in request")
	if "score" not in request.json or "story_id" not in request.json:
		abort(400,"score or story_id not in json:"+str(request.json.keys()))
	try:
		story_id = request.json["story_id"]
		score = request.json["score"]
	except ValueError:
		abort(400,"json[story_id] or json[score] not int")
	
	#get root, so we can differentiate queues/stales
	stories = query_db("SELECT * FROM stories WHERE id=?",(story_id,))
	if not stories:
		deleteStory(story_id)
		abort(400,"no matching story to id:"+str(story_id))
	curr = stories[0]
	format = formats[curr[1]]
	root = format['root']
	locks = list(curr[2:8])
	root_word = locks[root['index']]
	
	exec_db("UPDATE stories SET score=?,root=? WHERE id=?",(score,root_word,story_id))
	#TODO: something with stales...
	#mutate here! just copy stories entry (with corresponding holds entries), select word to mutate, set hold_i = mutating = selected wordN's holding entry, et voila (GET analogy will pick it up)!
	return make_response({},200)

#@app.route('/hieros/api/tasks/<int:task_id>', methods=['GET'])

if __name__ == '__main__':
	assert formats
	app.run(debug=True)
















































