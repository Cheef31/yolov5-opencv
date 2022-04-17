import datetime
import requests
import base64

url = 'https://hotel-infos.online/wp-json/wp/v2'

user = "Waleed499"
password = "9cWz IlHt qMtV XK6b sOQ8 Q38L"

creds = user + ':' + password

token = base64.b64encode(creds.encode())

header = {'Authorization': 'Basic ' + token.decode('utf-8')}

post = {
    'date': str(datetime.datetime.now() - datetime.timedelta(hours=2)),
    'title': '5 API Post',
    'content': 'This is the 5 API Post',
    'status': 'publish'
}

r = requests.post(url + '/posts', headers=header, json=post)
print(r.json())