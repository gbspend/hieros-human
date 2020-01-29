import requests,json
from sys import argv
url = 'http://localhost:5000/hieros/api/analogy'

word = "redo"
if len(argv) > 1:
	word = argv[1]

didOne = False
while True:
	r = requests.get(url)
	if not r.ok:
		print(r.status_code,"!!")
		exit(1)
	j = r.json()
	#print(j)
	if not j:
		break
	didOne = True
	p = j['prev_word']
	j['new_word'] = p+word
	r = requests.post(url, json=j)
	if not r.ok:
		print(r.status_code,"!!")
		exit(1)

if didOne:
	print("ALL DONE :D")
else:
	print("NONE")
