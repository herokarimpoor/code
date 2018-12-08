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

hostname = socket.gethostname()
def post(json, user_agent):
	headers = {
		"Content-Type": "application/json; charset=utf-8",
		"Accept": "application/json",
		"User-Agent": user_agent
	}
	while True:
		r2 =requests.post('http://contentapi.rasad.local/post/add', json=json, headers=headers)
		if r2.status_code == 200:
			return r2.content
		print user_agent, r2.content
		time.sleep(3)

def md5(fname):
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()

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

def file_properties(filename, path, crawl_time):
	_file_properties = {}
	try:
		if os.path.exists(filename):
			_file_properties = {
				'Create_Time' : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getctime(filename))),
				'Modify_Time' : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getmtime(filename))),
				'Crawl_Time' : time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(crawl_time))
			}
			mediainfo_file = path + "/" + os.path.basename(filename) + ".mediainfo"
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
	data = json.loads(requests.get('http://dashboard.rasad.local/meta').content)
	FIELDS = {}
	for i in data:
		FIELDS[data[i]['alias']] = i
	return FIELDS

def www_path(source, uri):
	path = ''
	#print uri
	keys = uri.replace(':','/').split('/')
	path += '/' + source 
	for i, path_section in enumerate(keys):
		if i < len(keys) - 1:
			path += '/' + path_section
	key = keys[-1]
	path += '/' + key[:1] 
	if len(key) > 1:
		path += '/' + key[1:3]
	path += '/' + key
	return 'http://' + socket.gethostbyname(hostname) + path

def www_path_fromfile(filename):
	return 'http://' + socket.gethostbyname(hostname) + os.path.dirname(filename)[19:]

def file_type(filename):
    kind = filetype.guess(filename)
    if kind is None:
        return ''
    ret = kind.mime.split('/')
    return ret[0] 

def get_path_from_key(source, uri, CONTENT_DIR):
    path = ''
    keys = uri.replace(':','/').split('/')
    path += '/' + source 
    for i, path_section in enumerate(keys):
        if i < len(keys) - 1:
            path += '/' + path_section
    key = keys[-1]
    path += '/' + key[:1] 
    if len(key) > 1:
        path += '/' + key[1:3]
    path += '/' + key
    if not os.path.exists(CONTENT_DIR + path):
        os.makedirs(CONTENT_DIR + path)    
    return CONTENT_DIR + path

def media_exists(source, key):
    headers = {
                "User-Agent": "DOURAN-"
    }
    content = requests.head('http://contentapi.rasad.local/posts/' + source + '/' + key + '/media', headers = headers)
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
    

def download(url, path, redis_client):
    if type(url) == list:
	url = url[0]
    file_name = url.split('/')[-1]
    counter = 0
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    u = urllib2.urlopen(url, timeout = 10, context=ctx)

    f = open(path + "/" + file_name, 'wb')
    try:
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
    except:
        print "Could not get Content-Length"
        pass
    print "Downloading: %s Bytes: %s  %3.2f MB" % (file_name, file_size, file_size/(1024*1024))
    file_size_dl = 0
    block_sz = 16 * 1024
    counter = 0
    t0= time.clock()
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]  %s " % (file_size_dl, file_size_dl * 100. / file_size, bitrate(file_size_dl,time.clock()  * 1000 - t0 * 1000) )
        status = status + chr(8)*(len(status)+1)
        print status,
        redis_client.set('downloader:progress:'+hostname, str(file_size) + ':' + str(file_size_dl * 100. / file_size))
        redis_client.expire('downloader:progress:'+hostname, 60)
    f.close()

    print " "
    if file_size_dl < file_size:
        syslog.syslog("Downloader, Download size mismatch %d / %d" % (file_size_dl, file_size))
        
    return path + "/" + file_name
# vim: tw=4 ts=4 et sw=4 smarttab autoindent smartindent
