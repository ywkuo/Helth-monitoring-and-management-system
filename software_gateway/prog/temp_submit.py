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
# 連接 MySQL 資料庫
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
            return False
        cnx.commit()		
        cnx.close()
        return True


devices = ["5002914f7d50"]



def msg_check(text):
    return 1
    print(type(text["mac"]))
    if (text["mac"] in devices):
        print("in")
        return 1


def data_process(text):
    global queue
    global mapping
    global par
    global location
    # default station
    station = "L00001"
    loc = "build1"
    f=open("upload.log","a")
    device=str(text["mac"])
    if device in mapping:
        station = mapping[device]
        loc = location[station]
        print(station+':'+loc)
    current = datetime.datetime.now()
    if text["id"] in pre:
        diff = current - pre[text["id"]]
        if diff.seconds < 10:
            print("time diff too short")
            return
    pre[text["id"]] = current            
    cmd="INSERT INTO TEMP (`mac`,`station`,`id`,`temperature`) VALUES ("+'\''+text["mac"]+'\','+'\''+loc+'\','+'\''+text["id"]+'\', '+'\''+text["temperature"]+'\')'
    queue.append(cmd)
    print(cmd)

    f.close()
    return
	

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
    client.subscribe(par['mqtt_submit'])

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")+":"+msg.topic+" "+str(msg.payload))
    tmp=msg.payload.decode("ascii")
    text = json.loads(tmp)
    result = msg_check(text)
    print(result)
    if result == 0:
        return
    if result == 1:
        data_process(text)
   
queue=[]
t = threading.Thread(target = database_insertion)
t.start()

pre=dict()  # record the last time for each uid	
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


