import psutil
import os
import time
def has(session_name):
    result = os.popen('ps -xo pid,cmd | grep SCREEN | grep -v grep').read()
    for command in result.split('\n'):
        tokens = command.split()
        if len(tokens)>0 and tokens[1] == 'SCREEN':
            for i in range(2,len(tokens) - 1): 
                if tokens[i] == '-S' and tokens[i + 1] == session_name:
                    return int(tokens[0])
    return None

def run_in_new_tab(session_name, command, title):
    if has(session_name):
        print "Screen [%s] Exists" % (session_name)
        result = os.popen('screen -S %s -Q windows'%(session_name)).read()
        window_index = len(result.split('  '))
        os.popen('screen -S %s -X screen %d'%(session_name, window_index)).read()
        os.popen('screen -S %s -p %d -X title "%s"'%(session_name, window_index, title)).read()
        print "Window %s created" % (title)
        time.sleep(1)
        os.popen('screen -S %s -p %d -X stuff "%s^M"'%(session_name, window_index, command)).read()
    else:
        print "Screen [%s] Created" % (session_name)
        result = os.popen('screen -dm -S %s'%(session_name)).read()
        os.popen('screen -S %s -p 0 -X title "%s"'%(session_name, title)).read()
        print "Window %s created" % (title)
        time.sleep(1)
        os.popen('screen -S %s -p 0 -X stuff "%s^M"'%(session_name, command)).read()
        


