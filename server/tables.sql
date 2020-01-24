CREATE TABLE IF NOT EXISTS "holds" (
	id integer PRIMARY KEY,
	story_id integer NOT NULL,
	i integer NOT NULL,
	node integer NOT NULL,
	prev_word text NOT NULL,
	par_word text NOT NULL,
	par_pos test NOT NULL
);
CREATE TABLE IF NOT EXISTS "nodes" (
	id integer PRIMARY KEY,
	pos text NOT NULL,
	word text NOT NULL,
	i integer NOT NULL,
	replacement integer,
	parent integer
);
CREATE TABLE IF NOT EXISTS "stories" (
	id integer PRIMARY KEY,
	form integer NOT NULL,
	word0 text NOT NULL,
	word1 text NOT NULL,
	word2 text NOT NULL,
	word3 text NOT NULL,
	word4 text NOT NULL,
	word5 text NOT NULL,
	hold integer NOT NULL,
	hold_i integer NOT NULL
);
CREATE TABLE IF NOT EXISTS "queues" (
	id integer PRIMARY KEY,
	story_id integer NOT NULL,
	story text NOT NULL,
	score integer NOT NULL,
	root text NOT NULL
);
CREATE TABLE IF NOT EXISTS "stales" (
	id integer PRIMARY KEY,
	story_id integer NOT NULL,
	root text NOT NULL,
	strikes integer NOT NULL
);