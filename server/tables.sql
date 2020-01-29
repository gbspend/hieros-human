CREATE TABLE IF NOT EXISTS "holds" (
	id integer PRIMARY KEY,
	story_id integer NOT NULL,
	i integer NOT NULL,
	node_ind integer NOT NULL,
	prev_word text NOT NULL,
	par_word text NOT NULL,
	par_pos text NOT NULL,
	UNIQUE(story_id, i)
);
CREATE TABLE IF NOT EXISTS "stories" (
	id integer PRIMARY KEY,
	form integer NOT NULL,
	word0 text,
	word1 text,
	word2 text,
	word3 text,
	word4 text,
	word5 text,
	hold_i integer NOT NULL,
	mutating integer,
	score integer
);
CREATE TABLE IF NOT EXISTS "bests" (
	id integer PRIMARY KEY,
	form integer NOT NULL,
	story text,
	score integer DEFAULT 0
);