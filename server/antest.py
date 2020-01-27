import requests,json
url = 'http://localhost:5000/hieros/api/analogy'

# GET
while True:
	r = requests.get(url)
	if not r.ok:
		print(r.status_code,"!!")
		exit(1)
	j = r.json()
	if not j:
		break
	j['new_word'] = "another"
	r = requests.post(url, json=j)
	if not r.ok:
		print(r.status_code,"!!")
		exit(1)

print("ALL DONE :D")
