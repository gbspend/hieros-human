from flask import Flask, jsonify, abort, make_response, request, g
import sqlite3
import pickle
from random import randint

app = Flask(__name__)

DATABASE = 'hieros.db'

#with open("formats.p") as f:
with open("formatssw.p","rb") as f:
	formats = pickle.load(f)

#something to store data (which stories are being worked on, etc)
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
#https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
'''
EXAMPLES:

@app.route('/hieros/api/analogy', methods=['GET'])
def get_tasks():
	exec_db("INSERT INTO stales(story_id,root,strikes) VALUES (1,'B',0)")
	for row in query_db('SELECT * FROM stales'):
		print(row)
	return jsonify({'tasks': 'this space intentionally left blank'})

@app.route('/hieros/api/analogy', methods=['POST'])
def insert_analogy():
	if not request.json or not 'title' in request.json:
		abort(400)
	task = {
		'id': tasks[-1]['id'] + 1,
		'title': request.json['title'],
		'description': request.json.get('description', ""),
		'done': False
	}
	#DO STUFF
	return jsonify({'task': task}), 201
'''
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
	r = parent['replace']
	if r:
		pword, ppos = r
	
	#get next holds id
	r = query_db("SELECT i FROM holds WHERE story_id=? ORDER BY i DESC", (story_id,))
	if not r:
		i = 0
	else:
		i = r[0]
	
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
	if 'i' not in request.json or 'word' not in request.json:
		abort(400)
	try:
		i = int(request.json['i'])
	except ValueError:
		abort(400)
	word = request.json['word'].strip()
	if not word or i >= len(formats):
		abort(400)

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
	r = query_db("SELECT * FROM stories WHERE hold_i<5 ORDER BY id")
	#(id, form, word0, word1, word2, word3, word4, word5, hold_i)
	if not r or all(row[0] in working for row in r):
		return make_response({},200) #nothing to work on (ask for something else)
	
	curr = [row for row in r if row[0] not in working][0]
	story_id = curr[0]
	format = formats[curr[1]]
	locks = curr[2:8]
	hold_i = curr[8]
	working.add(story_id)
	
	r = query_db("SELECT i,node_ind,prev_word,par_word,par_pos FROM holds WHERE story_id=? ORDER BY i", (story_id,))
	if not r:
		#delete from stories so we don't get caught in a loop when we GET analogy again
		deleteStory(story_id)
		abort(400)
	
	i,node_ind,prev_word,par_word,par_pos = r[hold_i]
	if i != hold_i:
		deleteStory(story_id)
		abort(400)
	
	root = format['root']
	node = findInd(root,node_ind)
	
	if locks[node['index']] is not None:
		#we're mutating!
		#fix for mutation: find first None lock, advance hold_i to that point, set it in stories entry, and re-query holds... and reset all remaining locks to None (traverse format[root]! :D)
			# so one update to stories: set new hold_i AND wordN's to None/NULL
		
		'''
		OOPS
		found = False
		for i,l in enumerate(locks):
			if l is None:
				found = True
				break
		if not found:
			deleteStory(story_id)
			abort(400)
		'''
		
		#figure out which sub-locks need to be None/NULL
		#exec_db("UPDATE stories SET word5='holo' WHERE id=?")
	
	#query = pword+" ("+ppos+") : "+node['word']+" ("+npos+") :: "+prev+" ("+ppos+") : _______ ("+npos+")"
	#how much to "checksum"? none? just sanity check that par_word/pos and node_word/pos match on the other side!
	return jsonify({'story_id':story_id, "par_word":par_word, "par_pos":par_pos, "node_word":node['word'], "node_pos":node['pos'], "prev_word":prev_word})

#receive analogy
@app.route('/hieros/api/analogy', methods=['POST'])
def insert_analogy():
	#sanity check that par_word/pos and node_word/pos match on this side
	keys = ["new_word", "node_pos", "node_word",  "par_pos",  "par_word",  "prev_word",  "story_id"]
	if not all([k in request.json for k in keys]):
		abort(400)
	
	

	return make_response({},200)

#=Score=======

#return next score needed
@app.route('/hieros/api/score', methods=['GET'])
def get_score():
	print(len(formats))
	return jsonify({'response': 'this space intentionally left blank'})

#receive score
@app.route('/hieros/api/score', methods=['POST'])
def insert_score():
	return make_response({},200)

#@app.route('/hieros/api/tasks/<int:task_id>', methods=['GET'])

if __name__ == '__main__':
	assert formats
	app.run(debug=True)
















































