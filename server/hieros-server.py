from flask import Flask, jsonify, abort, make_response, request

app = Flask(__name__)

#======================

import sqlite3
from flask import g

DATABASE = 'hieros.db'

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

def insert_db(query, args=()):
	db = get_db()
	db.execute(query, args)
	db.commit()
	return True

#=====================

@app.teardown_appcontext
def close_connection(e):
	db = g.pop('db', None)
	if db is not None:
		db.close()

@app.errorhandler(404)
def not_found(error):
	return make_response(jsonify({'error': 'Not found'}), 404)

#=====================
#https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
'''
EXAMPLES:

@app.route('/hieros/api/analogy', methods=['GET'])
def get_tasks():
	insert_db("INSERT INTO stales(story_id,root,strikes) VALUES (1,'B',0)")
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

#Analogy

#return next analogy needed
@app.route('/hieros/api/analogy', methods=['GET'])
def get_analogy():
	return jsonify({'response': 'this space intentionally left blank'})

#receive analogy
@app.route('/hieros/api/analogy', methods=['POST'])
def insert_analogy():
	return jsonify({'response': request.json})

#@app.route('/hieros/api/tasks/<int:task_id>', methods=['GET'])

if __name__ == '__main__':
	app.run(debug=True)











