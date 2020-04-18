import time
import timeout_decorator
import RPi.GPIO as GPIO
import subprocess
import re

GPIO.setmode(GPIO.BCM)


#RFID reader: RC522
import mfrc522
# Create an object of the class MFRC522
MIFAREReader = mfrc522.MFRC522()
 
# image related packages
import cv2
import sys
import numpy as np
from PIL import ImageFont, ImageDraw, Image
from picamera.array import PiRGBArray
from picamera import PiCamera
from pytesseract import image_to_string

# network
import paho.mqtt.client as mqtt
import smtplib


#-----------------------------
# function to move servo
def move():
    p=GPIO.PWM(13,50)
    p.start(7.3)
    time.sleep(0.05)
    p.ChangeDutyCycle(8.1)
    time.sleep(0.3)
    p.ChangeDutyCycle(7.3) 
    time.sleep(0.4)
    p.stop()
#-----------------------------
# function to read card UID for 10 seconds
#@timeout_decorator.timeout(10, timeout_exception=StopIteration)
def read_uid(mydraw):
    uid_str = ""
    pre_s = ''
    last_time = time.time()
    sleep_mode = False    
    while True:
        text = "card scanning.."
        if (time.time()>last_time+300):
            sleep_mode = True
            text = text + "...." 
        # determine to display second
        current_s = time.strftime("%S", time.localtime()) 
        if not (pre_s == current_s):
            current_time=time.strftime("%H:%M:%S", time.localtime())
            text = text+current_time
            mydraw.output_text(text,10,150)
        
        # Scan for cards
        (status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
 
        # Get the UID of the card
        (status,uid) = MIFAREReader.MFRC522_Anticoll()
 
        # If we have the UID, continue
        if status != MIFAREReader.MI_OK:
            if (sleep_mode):
                time.sleep(1)
            else:
                time.sleep(0.1)
            continue       # go back to read ID card
        # Construct the UID string in NCNU CC format (10 digit)
        last_time = time.time()
        sleep_mode = False
        uid_str=str(int((hex(uid[3])+hex(uid[2])+hex(uid[1])+hex(uid[0])).replace("0x",""),16))
        for i in range(10-len(uid_str)):
             uid_str = "0"+uid_str
        print(uid_str)
        break
	
    mydraw.output_text("Measuring in 10 seconds",10,150)    
    mydraw.clear(200,400)
    return  uid_str       

#-----------------------------
# function to check distance for 10 seconds
@timeout_decorator.timeout(10, timeout_exception=StopIteration)
def check_distance(threshold):
    # Check distance. Turn on when distance < threshold
    # Remark: using adafruit_hcsr04 is not recommanded because of high CPU usage 
    while True:
        GPIO.output(5,GPIO.LOW)
        time.sleep(0.0001)
        GPIO.output(5,GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(5,GPIO.LOW)
        d1 = GPIO.input(6)
        while True:
            if (not d1 == GPIO.input(6)):
                s = time.monotonic()
                d2 = GPIO.input(6)
                break
        while True:
            if (not d2 == GPIO.input(6)):
                e = time.monotonic()
                break
        dist = (e-s)*1000000/58
        if dist<threshold:
            break
        time.sleep(0.1)
    

#---------------------------
# fuction for "image to 7 segment number. copy crop to target img
def if_exist(img,x1,y1,x2,y2):
    count = 0
    for i in range(x2-x1):
        for j in range(y2-y1):
            if (img[y1+j][x1+i]==0):
                count = count+1
                img[y1+j][x1+i]= 128
            else:
                img[y1+j][x1+i] = 200
#                if count > 10:
#                    break
    if count>6:
        return True
    else:
        return False

def get_value(img,digit,x,y):
    seven=[[3,6,8,25],[1,34,6,53],[11,0,16,5],[9,27,14,32],[7,55,12,60],[16,6,21,25],[13,34,18,53]]
    mapping={0:'',96:'1',62:'2',124:'3',105:'4',93:'5',95:'6',100:'7',127:'8',125:'9',119:'0',19:'L',107:'H'}
    value=0
    d=1
    if digit==0:
        x=x
    if digit==1:
        x=x+22
    if digit==2:
        x=x+45
    for i in range(7):
        r=if_exist(img,x+seven[i][0],y+seven[i][1],x+seven[i][2],y+seven[i][3])
        if r:
            value=value+d
        d=d<<1
#        print(str(i)+':'+str(r))
    ch=''
#    print(value)
    try:
        ch=mapping[value]
    finally:
        return ch

def ocr(mydraw):
    print("start OCR: "+str(time.monotonic()))
    mydraw.output_text("Screen",10,210)
       # crop area
    x1=250
    y1=80
    x2=440
    y2=300
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)
    ret,image = cap.read()
    image = cv2.rotate(image,cv2.ROTATE_180)
    crop=image[y1:y2,x1:x2,:]
        # preprocessing: otsu thresholding to binary image
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray,(5,5),0)
    ret3,th3 = cv2.threshold(blur,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        # determine LCD screen location. Find y first.
    print("thresholding done: "+str(time.monotonic()))
    for i in range(th3.shape[0]):
        if (255 in th3[i,:]):
            y=i
            break;
        # determine LCD screen location. x is determined by the line 15 pexel below y
    x = np.where(th3[y+15,:]==255)
#    print(len(x[0]))

        # return null string if a black screen detected (fail to trigger)
    if len(x[0])==0:
        return ""
    x=(x[0][0]+x[0][len(x[0])-1])//2
         # determine left-top pixel of region of interest
    x=x-28
    y=y+62
    if not x>0:
        return ""
#    print("...")
#    print(x)
#    print(y)

    mydraw.paste(crop[y:y+60,x:x+70],200,210)

        # process 1st digit
    digit1 = get_value(th3,0,x,y)
    temp_str = ''
    if digit1=='L':
        temp_str = 'L'
    elif digit1 =='H':
        temp_str = 'H'
    elif digit1=='3' or digit1=='4':
        temp_str = digit1 + get_value(th3,1,x,y) + get_value(th3,2,x,y)
    print("OCR done: "+str(time.monotonic()))
    fname="/home/pi/images/"+time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime())+".jpg"
    file = open("/home/pi/temp_submit/result.txt","a")
    file.write(fname+":"+temp_str+"\n")
    cv2.imwrite(fname,crop)
    file.close()
    cap.release()
    del cap
    th3 =  th3[y:y+60,x:x+70]
    th3 = cv2.cvtColor(th3, cv2.COLOR_GRAY2BGR)
    mydraw.paste(th3,350,210)
    return temp_str

#---------------------------
# function to process output string
def generate_output(mydraw,mynet,sound,in_str,uid):
    temp="0" 
    print(in_str)
    print(len(in_str))
    if len(in_str) == 0 :
        mydraw.output_text("Fail... Try again"+in_str,10,350)
        sound.error_sound1()
    elif (in_str[0]=='L') :
        mydraw.output_text("Temp too low, try again"+in_str,10,350)
        sound.error_sound1()
    elif in_str[0]=='H':
        text = "Over temp"+in_str
        temp = '42'
        mydraw.output_text(text, 10,350)
        mynet.send_message_by_email(temp,uid)    
        sound.error_sound2()    
    elif len(in_str) != 3 :
        mydraw.output_text("Fail... Try again"+in_str,10,350)
        sound.error_sound1()
    else:    
        temp = in_str[0:2]+"."+in_str[2]
        text = "Temp="+temp 
        if float(temp)>37.5:
            text = text +" Temp too high"+in_str
            mynet.send_message_by_email(temp,uid)
            sound.error_sound2()
        mydraw.output_text(text, 10,350)

    return temp 

#---------------------------
# buzzer class
class Buzzer():
    def __init__(self, pin):
        self.pin = pin 
        GPIO.setup(pin,GPIO.IN) 
        
    def beep(self,duration,freq):
        GPIO.setup(self.pin,GPIO.OUT)
        for i in range(duration):
            GPIO.output(self.pin,GPIO.HIGH)
            time.sleep(freq) # Delay in seconds
            GPIO.output(self.pin,GPIO.LOW)
            time.sleep(freq)
        GPIO.setup(self.pin,GPIO.IN)

    def error_sound1(self):
        self.beep(30,0.0005)
        time.sleep(0.1)
        self.beep(10,0.001)
        time.sleep(0.1)
        self.beep(30,0.0005)
        time.sleep(0.1)
	
    def error_sound2(self):
        for i in range(10):
            self.beep(30,0.0005)
            time.sleep(0.1)
            
#---------------------------
# Handle network tasks 
class Network_agent():
    def __init__(self):
        return

    def getMAC(self,interface='wlan0'):
  # Return the MAC address of the specified interface
        try:
            mac = open('/sys/class/net/%s/address' %interface).read()
            mac = mac.replace(':','')
            mac = mac.replace('\n','')
        except:
            mac = "000000000000"
        return mac
    def getIP(self):
        result = str(subprocess.run(['ifconfig', 'eth0'], stdout=subprocess.PIPE))
        ip=''
        try:
            ip=re.search('inet(.+?)netmask', result).group(1)
        except:
            print ("no eth0")
        if (not ip):
            result = str(subprocess.run(['ifconfig', 'wlan0'], stdout=subprocess.PIPE))
            try:
                ip=re.search('inet(.+?)netmask', result).group(1)
            except:
                print ("no wlan0")
        print(ip)
        return str(ip) 
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))

    def start(self):
        self.macaddress = self.getMAC('wlan0')
        while True:
            self.ipaddress = self.getIP()
            if (self.ipaddress): 
                break
            time.sleep(1)
        print("MAC address = "+self.macaddress)
        self.gmail_sender = 'XXX@gmail.com'
        self.gmail_passwd = 'XXX'
        self.TO = 'XXX@gmail.com'
        self.SUBJECT = '*** Warning from AUTO-Thermometer System ***'
        # mqtt message
        self.MQTT_IP = "XXX"
        self.MQTTT_Port = 1883 #port
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.username_pw_set(username="XXX", password="XXX")
        while True:
            try:
                self.client.connect(self.MQTT_IP , self.MQTTT_Port)
            except:
                print("MQTT Broker is not online. Connect later.")
                time.sleep(5)
                continue
            self.client.loop_start()

            break
    def send_message_by_email(self,temp,uid):
        self.TEXT = uid+':'+temp
        self.BODY = '\r\n'.join(['To: %s' % self.TO,
                    'From: %s' % self.gmail_sender,
                    'Subject: %s' % self.SUBJECT,
                    '', self.TEXT])
        print(self.BODY)
        try:
            self.server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            self.server.ehlo()
            self.server.login(self.gmail_sender, self.gmail_passwd)
            self.server.sendmail(self.gmail_sender, self.TO, self.BODY)
            self.server.close()
        except:
            print ('error sending mail')

    def send_mqtt(self,card_id,temp):
#        print(self.client.is_connected())
        text = '{"mac":"'+self.macaddress+'","id":"'+card_id+'","temperature":"'+temp+'"}'
        if (not self.client.is_connected()):
            print("reconnect")
            self.res = self.client.reconnect()   
        for i in range(3):  # try max 3 times
            self.result = self.client.publish("TEMP",text,1)
            start_time= time.time()
            while time.time()<start_time+3:
                self.res = self.result.is_published()
                if (self.res):
                    break
                time.sleep(0.1)
            print("pub")
            print(self.res)           
            if (self.res):
                break
        return self.res 


#---------------------------
# Handle screen tasks     
class Screen_out():
    def __init__(self, name, width, length):
        self.name = name
        self.fontPath = "/home/pi/temp_submit/TW-Kai-98_1.ttf"   # *** you can use your own font ***
        self.font = ImageFont.truetype(self.fontPath, 50, encoding="utf-8")
        self.img = np.zeros((length,width, 3), np.uint8)
        self.img[:] = (255, 255, 255)
        cv2.namedWindow(self.name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(self.name,0,0)
        cv2.resizeWindow(self.name, 1000, 700)
    
    def output_text(self, text, x, y):
        self.img[y:y+50,x:,:] = [255,255,255]
        imgPil = Image.fromarray(self.img)
        draw = ImageDraw.Draw(imgPil)
        draw.text((x, y),  text,  font = self.font,fill = (0, 0, 0))
        self.img =  np.array(imgPil)
        cv2.imshow(self.name, self.img)
        cv2.waitKey(10)   

    def clear(self, y, h):
        self.img[y:y+h,:,:] = [255,255,255]
        cv2.imshow(self.name, self.img)
        cv2.waitKey(10)

    def paste(self,crop,x,y):
        self.img[y:y+crop.shape[0],x:x+crop.shape[1]]=crop

#---------------------------
# initialization variables

# servo configuration
#GPIO.setmode(GPIO.BCM)
GPIO.setup(13, GPIO.OUT)
#p = GPIO.PWM(13, 50)
#p.start(7.5)

# sonar
GPIO.setup(5, GPIO.OUT)
GPIO.setup(6, GPIO.IN)

# sound object
sound = Buzzer(23)

# network task object
mynet = Network_agent()
mynet.start()


# screen drawing object
mydraw=Screen_out("NCNU cloud based AUTO Thermometer",1000,700)
text = " Welcome to NCNU\n   Cloud Auto-Thermometer System"
mydraw.output_text(text,10,10)
text = mynet.macaddress+mynet.ipaddress
mydraw.output_text(text,10,510)
 
move()
# main loop. until Ctrl-C pressed.
try:

    while True: 
        card_id = read_uid(mydraw)
        sound.beep(100,0.0001)
        time.sleep(0.4)        
        try:        
            check_distance(12)
        except StopIteration:
            continue    # go back        
    
    #---------------------
    # Turn on thermometer
        move()   
        result = ocr(mydraw)
        temp = generate_output(mydraw,mynet,sound,result,card_id)
        if temp=="0":
            continue

    # mqtt publish
        if mynet.send_mqtt(card_id,temp):
            text = "Upload complete"
        else:
            text = "Timeout"		

        mydraw.output_text(text,10,400)

        
except KeyboardInterrupt:
    GPIO.cleanup()
    cv2.destroyAllWindows()

finally:
    GPIO.cleanup()
    cv2.destroyAllWindows()
