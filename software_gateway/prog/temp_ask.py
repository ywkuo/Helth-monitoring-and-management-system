import paho.mqtt.client as mqtt
import json  
import datetime
import mysql.connector
import sys
import requests
import threading
import time

def database_insertion():
    global queue
    while True:
        if queue:
#            print("len="+str(len(queue))+":"+queue[0])
            if (insert_sql(queue[0])):
                queue.pop(0)
            else:
                print(datetime.datetime.now().isoformat()+":sql failure")
        time.sleep(1)


def insert_sql(cmd):
    global par
    try:
        cnx = mysql.connector.connect(host=par['sql'],user=par['sql_name'], passwd=par['sql_passwd'], db=par['db'], port = par['sql_port'])
    except mysql.connector.Error as err:
        print(err)
        return False 	
    else:
        cursor = cnx.cursor()
        print(cmd)
        try:
            cursor.execute(cmd)
        except mysql.connector.Error as err:
            print(err)
            cnx.commit()		
            cnx.close()            
            return False
        cnx.commit()		
        cnx.close()
        return True

def select_sql(cmd):
    global par
    try:
        cnx = mysql.connector.connect(host=par['sql'],user=par['sql_name'], passwd=par['sql_passwd'], db=par['db'], port = par['sql_port'])
    except mysql.connector.Error as err:
        print(err)
        return False
    else:
        cursor = cnx.cursor()
#        print(cmd)
        try:
            cursor.execute(cmd)
        except mysql.connector.Error as err:
            print(err)
            cnx.commit()		
            cnx.close()            
            return []
        records=cursor.fetchall()
        cnx.commit()
        cnx.close()
        return records


def data_process(text):
    global mapping
    global locations
    global par
    global queue
    station = "L00001"
    device = str(text["mac"])
    if device in mapping:
        station = mapping[device]
    loc = location[station]
    print(loc)
    cmd = "SELECT * FROM `TEMP` WHERE id ="+text["id"]+" and updatetime >'"
    cmd=cmd+datetime.date.today().isoformat()+" 00:00:00'"
    print(cmd)
    f=open("check.log",'a')    
    f.write(datetime.datetime.now().isoformat()+":"+cmd+'\n')
    for i in range(3):  #try three times
        result = select_sql(cmd)
        if result:
            break;
        time.sleep(0.2)
        
    if (result):
        f.write(str(result)+'\n')
        cmd='2'
        for e in result:
            f.write(str(e[6])+'\n')
            if e[6]>37.5:
                cmd='3'

    f.write(cmd+'\n')
    f.close()
    if (cmd):
        client.publish(par['mqtt_check']+"/"+text["mac"],cmd)
    cmd="INSERT INTO TEMP_CHECK (`mac`,`station`,`id`,`result`) VALUES ("+'\''+text["mac"]+'\', \''+loc+'\',\''+text["id"]+'\',\''+cmd+'\')'
    queue.append(cmd)
    return
	

def hex_string(in_data):
    num=0
    table=[48,49,50,51,52,53,54,55,56,57,65,66,67,68,69,70]
    for i in range(0,4): 
        num=num*16+table.index(ord(in_data[i].upper()))
    return str(num)+" "
def hex_int(in_data):
    num=0
    table=[48,49,50,51,52,53,54,55,56,57,65,66,67,68,69,70]
    for i in range(0,4): 
        num=num*16+table.index(ord(in_data[i].upper()))
    if num>32767 :
        num=-(65535-num+1)
    return num
def to_ten_digit(in_data):
    if (len(in_data))==10:
        return in_data
    out=''
    for i in range(0,10-len(in_data)):
        out='0'+out
    return (out+in_data)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global par
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(par['mqtt_check'])

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(datetime.datetime.now().isoformat()+":"+msg.topic+" "+str(msg.payload))
    type(msg.payload)
    tmp=msg.payload.decode("ascii")
    text = json.loads(tmp)
    data_process(text)
   
queue=[]
t = threading.Thread(target = database_insertion)
t.start()
	
try:
    f=open("config.txt","r")
except:
    print("unable to open config.txt")
    sys.exit(0)	
par = f.read()
par = par.replace('\n','')
par = json.loads(par)    
f.close()



try:
    f=open("location.txt","r")
except:
    print("unable to open location.txt")
    sys.exit(0)
location = f.read()
location = location.replace('\n','')
location = json.loads(location)
f.close()


try:
    f=open("mapping.txt","r")
except:
    print("unable to open mapping.txt")
    sys.exit(0)
mapping = f.read()
mapping = mapping.replace('\n','')
mapping = json.loads(mapping)
f.close()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(username=par['mqtt_name'], password=par['mqtt_passwd'])
client.connect(par['mqtt'], par['mqtt_port'])
client.loop_forever()


