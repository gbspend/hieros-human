import requests,json
url = 'http://localhost:5000/hieros/api/analogy'

while True:
	r = requests.get(url)
	if not r.ok:
		print(r.status_code,"!!")
		exit(1)
	j = r.json()
	print(j)
	if not j:
		break
	p = j['prev_word']
	j['new_word'] = p+"+redo"
	r = requests.post(url, json=j)
	if not r.ok:
		print(r.status_code,"!!")
		exit(1)

print("ALL DONE :D")
