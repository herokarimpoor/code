import requests
import hashlib
import json
import syslog
import time 
import socket
import configparser

config = configparser.ConfigParser()
config.read('/opt/rasad/common/config.ini')
hostname = socket.gethostname()
data = json.loads(requests.get(config['CONFIG']['dashboard'] + '/meta').content)

FIELDS = {}
ISUSER = {}
FIELDS_TYPE = {}

for i in data:
    FIELDS[data[i]['alias']] = data[i]['key']
    FIELDS_TYPE[data[i]['alias']] = data[i]['type']
    ISUSER[data[i]['alias']] = data[i]['is_user']

def md5(string):
   # hash_md5 = hashlib.md5()
   # hash_md5.update(string)
    return '000000000000'#hash_md5.hexdigest()

def post_db(json_params, user_agent = 'DOURAN-Crawler'):
	headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": user_agent + '/' + hostname
        }

	session =requests.session()
	while True:
		#print "===>", json_params
		r2 =session.post('http://contentapi.rasad.local/post/add', json=json_params, headers=headers)
		if r2.status_code == 200:
			#print "RESPONSE:", r2.content
			return r2.content
		#print r2.content
		#time.sleep(3)



def post_tag(params, user_agent = 'DOURAN-Crawler'):
	session =requests.session()
	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"Accept": "application/json",
		"User-Agent": user_agent + '/' + hostname
	}
	while True:
		r2 =session.post('http://contentapi.rasad.local/post/tag', params = params, headers = headers)
		if r2.status_code == 200:
			return r2.content
		time.sleep(3)

def log(msg):
	print msg
	syslog.syslog(msg)
  

