import psutil
import os
import time
import subprocess
       
def has(session_name):
    #result = os.popen('ps -xo pid,cmd | grep SCREEN | grep -v grep').read()
    #result = subprocess.check_output(['ps', '-xo', 'pid,cmd','|' , 'grep', 'SCREEN' ,'|' , 'grep', '-v', 'grep'])
    result = subprocess.check_output(['ps', '-x', '-opid,cmd'])
    for command in result.split('\n'):
        if not command.find('SCREEN'):
            continue
        tokens = command.split()
        if len(tokens)>0 and tokens[1] == 'SCREEN':
            for i in range(2,len(tokens) - 1): 
                if tokens[i] == '-S' and tokens[i + 1] == session_name:
                    return int(tokens[0])
    return None

def window_index(session_name, window_name):
    #result = os.popen('screen -S %s -Q windows'%(session_name)).read()
    print "111\n"
    result = subprocess.check_output(['screen','-S',session_name ,'-Q', 'windows'])
    print result
    print ">%s<"%(window_name)

    for index, wind in enumerate(result.split('  ')):
        tt = wind.split(' ')
        if len(tt) == 2 and tt[1] == str(window_name):
	    print "Return ", index
            return index

    index += 1
    print index
    os.system('screen -S %s -X screen %d'%(session_name, index))
    os.system('screen -S %s -p %d -X title "%s"'%(session_name, index, window_name))
    return index


def run_in_new_tab(session_name, command, title):
    if has(session_name):
        print "Screen [%s] Exists" % (session_name)
        w_index = window_index(session_name, title)
        print "Index of window:", w_index

        print "Window %s created" % (title)
        time.sleep(1)
        os.system('screen -S %s -p %d -X stuff "%s^M"'%(session_name, w_index, command))
    else:
        print "Screen [%s] Created" % (session_name)
        result = subprocess.check_output(['screen', '-dm', '-S', session_name, '/bin/bash'])
        os.system('screen -S %s -p 0 -X title "%s"'%(session_name, title))
        print "Window %s created" % (title)
        time.sleep(1)
        os.system('screen -S %s -p 0 -X stuff "%s^M"'%(session_name, command))
        


