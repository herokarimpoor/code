import xml.etree.ElementTree
import requests
import hashlib
import json
import socket
import filetype
import os
import urllib2
import sys
import time
import subprocess
import ssl
import syslog
import imghdr
import shlex
import redis
import socket
import gearman
import configparser

hostname = socket.gethostname()
config = configparser.ConfigParser()
config.read('/opt/rasad/common/config.ini')
data = json.loads(requests.get(config['CONFIG']['dashboard'] + '/meta').content)
douran_session = None

FIELDS = {}
ISUSER = {}
FIELDS_TYPE = {}

for i in data:
        FIELDS[data[i]['alias']] = data[i]['key']
        FIELDS_TYPE[data[i]['alias']] = data[i]['type']
        ISUSER[data[i]['alias']] = data[i]['is_user']

def post(json, user_agent):
	global config
	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"Accept": "application/json",
		"User-Agent": user_agent
	}
	while True:
		try:
			t = time.time()
			r2 = douran_request().post(config['CONFIG']['contentapi_post_add']+'/post/add', json=json, headers=headers)
			print config['CONFIG']['contentapi_post_add']+'/post/add'," Duration=", time.time() - t, r2.status_code
			#print "reponse:"
			#print r2.json()
			if r2.status_code == 200:
				return r2.content
		except Exception as e:
			print "============================= Exception ============================="
			print e
			douran_session = None
		time.sleep(3)

def md5(fname):
	#hash_md5 = hashlib.md5()
	#with open(fname, "rb") as f:
	#	for chunk in iter(lambda: f.read(4096), b""):
	#		hash_md5.update(chunk)
	return ''

def duration_to_sec(duration):
	sec = 0
	try:
		for i in duration.split(" "):
			if i.endswith("h"):
				sec += int(i.replace("h", "")) * 3600
			if i.endswith("ms"):
				sec += 0
			if i.endswith("mn"):
				sec += int(i.replace("mn", "")) * 60
			if i.endswith("s"):
				sec += int(i.replace("s", "")) 
	except:
		print "Exeption in duration_to_sec: " + duration
	return sec

def file_properties(filename):
	_file_properties = {}
	try:
		if os.path.exists(filename):
			_file_properties = {
				'Create_Time' : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getctime(filename))),
				'Modify_Time' : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getmtime(filename))),
				'Crawl_Time' : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time()))
			}
			mediainfo_file = os.path.dirname(filename) + "/" + os.path.basename(filename) + ".mediainfo"
			subprocess.call("mediainfo  "+filename+" --Output=XML --logfile=" + mediainfo_file + " > /dev/null" , shell=True)
			e = xml.etree.ElementTree.parse(mediainfo_file).getroot()
			for k in e.findall('.//File/track[@type="General"]/*'):
				_file_properties['General_' + k.tag] = k.text
			for k in e.findall('.//File/track[@type="Video"]/*'):
				_file_properties['Video_' + k.tag] = k.text
			for k in e.findall('.//File/track[@type="Audio"]/*'):
				_file_properties['Audio_' + k.tag] = k.text
	except:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		print(exc_type, fname, exc_tb.tb_lineno)
	return _file_properties

def updateClientAPIMetaTag():
	global config
	while True:
		try:
			data = json.loads(douran_request().get(config['CONFIG']['dashboard'] + '/meta').content)
			break
		except Exception as e:
			print "============================= Exception ============================="
			print e

	FIELDS = {}
	for i in data:
		FIELDS[data[i]['alias']] = i
	return FIELDS

def www_path(source, uri):
	global config
	path = 'http://' + socket.gethostbyname(hostname) 
	path += config['CONFIG']['content_pre']
	path += '/' + source

	keys = uri.replace(':','/').split('/')
	for i, path_section in enumerate(keys):
		if i < len(keys) - 1:
			path += '/' + path_section
	key = keys[-1]
	path += '/' + key[:1] 
	if len(key) > 1:
		path += '/' + key[1:3]
	path += '/' + key
	return path

def www_path_fromfile(filename):
	global config
	return 'http://' + socket.gethostbyname(hostname) + os.path.dirname(filename)[(len(config['CONFIG']['content_dir'])):] + '/'

def abs_path(source, uri):
	global config
	path =  config['CONFIG']['content_dir']
	path += config['CONFIG']['content_pre']
	path += '/' + source

	keys = uri.replace(':','/').split('/')
	for i, path_section in enumerate(keys):
		if i < len(keys) - 1:
			path += '/' + path_section
	key = keys[-1]
	path += '/' + key[:1] 
	if len(key) > 1:
		path += '/' + key[1:3]
	path += '/' + key
	return path

def file_type(filename):

	kind = filetype.guess(filename.encode('ascii','replace'))
	if kind is None:
		if filename[-3:] == 'mkv':
			return 'video'
		return ''
	ret = kind.mime.split('/')
	return ret[0] 

def is_image(img):
	ex = imghdr.what(img)
	return ex == 'jpeg' or ex == 'gif' or ex == 'jpg' or ex == 'png'

def media_exists(source, key):
	global config
	headers = {
				"User-Agent": "DOURAN-"
	}
	medias = ['video', 'image', 'audio']

	for media in medias:
		while True:
			try:
				content = douran_request().head(config['CONFIG']['contentapi_media_exists'] + '/posts/%s/%s/%s'%(source, key, media), headers = headers)
				break
			except Exception as e:
				print "============================= Exception ============================="
				print e
				douran_session = None

		if content.status_code == 200:
			print "Content Exists   " + source + ':' + key
			return True
	return False


def bitrate(size, time):
	size = int(size)*8 
	v = size / time
	if v > (1024 * 1024 * 1024):
		return "%3.2f Gbps" % (v / (1024 * 1024 * 1024))
	if v > (1024 * 1024):
		return "%3.2f Mbps" % (v / (1024 * 1024))
	if v > (1024):
		return "%3.2f Kbps" % (v / (1024))
	
def download(url, path, redis_client, sid):
	if not os.path.exists(path):
		os.makedirs(path)
	if type(url) == list:
		url = url[0]
	file_name = url.split('/')[-1]
	cmd = "wget %s -O %s/%s"%(url, path, file_name)
	print cmd
	if (True):
		os.system(cmd)
	else:
		proc = subprocess.Popen(shlex.split(cmd),
							stdout=subprocess.PIPE, 
							stderr=subprocess.PIPE)
		hostname = socket.gethostname()
		while True:
			line = proc.stderr.readline()
			if len(line) >= 75 and len(line) < 85:
				redis_client.set('downloader:%s:out'%(sid), line)
				redis_client.set('downloader:%s:host'%(sid), hostname)
				redis_client.set('downloader:%s:url'%(sid), url)
				redis_client.set('downloader:%s:vol'%(sid), line[:8].strip())
				redis_client.set('downloader:%s:percent'%(sid), line[62:65].strip())
				redis_client.set('downloader:%s:bandwith'%(sid), line[67:73].strip())
				redis_client.set('downloader:%s:elapse'%(sid), line[72:].strip())

				redis_client.expire('downloader:%s:out'%(sid), 1800)
				redis_client.expire('downloader:%s:host'%(sid), 1800)
				redis_client.expire('downloader:%s:url'%(sid), 1800)
				redis_client.expire('downloader:%s:vol'%(sid), 1800)
				redis_client.expire('downloader:%s:percent'%(sid), 1800)
				redis_client.expire('downloader:%s:bandwith'%(sid), 1800)
				redis_client.expire('downloader:%s:elapse'%(sid), 1800)
				#print line,
			if line == '' and proc.poll() != None:
				break	

	if os.path.exists(path):
		statinfo = os.stat("%s/%s"%(path, file_name))
		if statinfo.st_size == 0:
			os.remove("%s/%s"%(path, file_name))
			return None
	else:
		return None
	return "%s/%s"%(path, file_name)

def check_gearman(job_request):
	if job_request.complete:
		print "Job %s finished!  Result: %s" % (job_request.job.unique, job_request.state)
	elif job_request.timed_out:
		print "Job %s timed out!" % job_request.unique
		raise ValueError('Job submit timed out')
	elif job_request.state == JOB_UNKNOWN:
		raise ValueError('Error in gearman state')

def douran_request():
	global douran_session
	if douran_session is None:
		douran_session = requests.Session()
		douran_session.headers.update({'User-Agent': 'DOURAN-crawler/general'})
	return douran_session
	

def post_tag(params, user_agent = 'DOURAN-Crawler'):
	global config
	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"Accept": "application/json",
		"User-Agent": user_agent + '/' + hostname
	}
	while True:
		try:
			r2 = douran_request().post(config['CONFIG']['contentapi_post_add'] + '/post/tag', params = params, headers = headers)
			if r2.status_code == 200:
				return r2.content
		except Exception as e:
			print "============================= Exception ============================="
			print e
			time.sleep(3)
			douran_session = None


def log(msg):
	print msg
	syslog.syslog(msg)
  

