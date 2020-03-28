// Screener software
// https://github.com/ywkuo/Helth-monitoring-and-management-system
// Copyright (C) 2020 by Yaw-Wen Kuo, National Chi Nan University, Taiwan
// GNU GPL v3.0, https://www.gnu.org/licenses/gpl.html
//
// ** Fill wifi ssid, password, mqtt ip, mqtt port, mqtt user name
// ** mqtt password before uploading to wemos di mini
// ** The following packages are required.
// Used library: PubSubClient, MFRC522, LiquidCrystal_I2C
// 
// Functions:
// 1. connecting to wifi (if not, reboot)
// 2. RFID reading
// 3. query the software gateway by MQTT (will try 3 times)
//    success of publishing is confirmed by the message from software gateway
//    Remark: I only use QoS=0 because I don't have to verify QoS=1.
// 4. Output data on LCD screen and generate a sound.
//    4 cases:
//    case 0: UID is not in the private database of NCNU
//    case 1: No temperature value corresponding to this UID today
//    case 2: Temperature is normal for this UID  
//    case 3: Over temerature for this UID
// 5. MQTT publish topic: "TEMP_CHECK"
//    payload format: {"mac":MACaddress,"id":UID}
// 6. MQTT subscribe topic: "TEMP_CHECK/device_macaddress"
//    payload format: none, just one byte (0, 1, 2, or 3) 

#include <ESP8266WiFi.h>
#include <PubSubClient.h>


//----------------------
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN D8
#define RST_PIN D0

MFRC522 mfrc522(SS_PIN, RST_PIN);  // Create MFRC522 instance

//-----------------------

#include <Wire.h> // I2C library, required for MLX90614


#define buzzer D4
//---------------------------
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27,20,4);  // set the LCD address to 0x27 for a 16 chars and 2 line display

//------------------------- network


const char* ssid     = "";  //wifi ssid 
const char* password = "";  //wifi password

//arduino to mqtt
char* mqtt_server = " "; // your mqtt server ip
int mqtt_port = 1883;
char mqtt_clientID[20];  // automatically use MAC address as client ID
char* mqtt_username = "";  // mqtt user name
char* mqtt_password = "";   // mqtt password
char* mqtt_publish_topic1 = "TEMP_CHECK";  // this is my topic, your can use any
WiFiClient espClient;
PubSubClient client(espClient);
String MacAddress;
int c;
char msg[100];
int no;

//-----------------------------------------------
String  print2HEX(int number) {
  String ttt ;
  if (number >= 0 && number < 16)
  {
    ttt = String("0") + String(number,HEX);
  }
  else
  {
      ttt = String(number,HEX);
  }
  return ttt ;
}

String GetWifiMac()
{
   uint8_t MacData[6];
   String t1,t2,t3,t4,t5,t6,tt ;  
   WiFi.status();    //this method must be used for get MAC
   WiFi.macAddress(MacData);
  
   Serial.print("Mac:");
   Serial.print(MacData[0],HEX) ;
   Serial.print("/");
   Serial.print(MacData[1],HEX) ;
   Serial.print("/");
   Serial.print(MacData[2],HEX) ;
   Serial.print("/");
   Serial.print(MacData[3],HEX) ;
   Serial.print("/");
   Serial.print(MacData[4],HEX) ;
   Serial.print("/");
   Serial.print(MacData[5],HEX) ;
   Serial.print("~");
   
   t1 = print2HEX((int)MacData[0]);
   t2 = print2HEX((int)MacData[1]);
   t3 = print2HEX((int)MacData[2]);
   t4 = print2HEX((int)MacData[3]);
   t5 = print2HEX((int)MacData[4]);
   t6 = print2HEX((int)MacData[5]);
   tt = (t1+t2+t3+t4+t5+t6);
   Serial.println(tt);
  
   return tt ; 
}

void WIFI_Connect()
{
  //digitalWrite(powerled,HIGH);
  WiFi.disconnect();
  Serial.println("Booting Sketch...");
  WiFi.mode(WIFI_AP_STA);
  WiFi.begin(ssid, password); 
  Serial.println("connecting");
  int a=0;
  while(WiFi.status() != WL_CONNECTED)
  {
    a++;
    delay(1000);
    Serial.println(a);
     if(a>15){
       break;
       }
    
  } // Wait for connection  
  if(WiFi.status() != WL_CONNECTED) 
  {
    Serial.println("resetting"); 
    while (1){};
  }

}

void reconnect() {
  // Loop until we're reconnected
  String topic;
  int k=0;
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    delay(1000);
    k++;
  
    // Attempt to connect
    if (client.connect(mqtt_clientID,mqtt_username,mqtt_password)) {
      Serial.println("connected");
      
      //Subscribe
      topic=mqtt_publish_topic1;
      topic=topic+"/"+MacAddress;
      topic.toCharArray(msg,100);
      client.subscribe(msg);
      Serial.println(msg);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(1000);
    }
    if(k>5){
          break;
    }
  }
  if(!client.connected()) 
  {
  Serial.println("resetting"); 
    while (1) {};
  }
}
long get_uid(byte *input)
{
  union value{
    unsigned long v;
    byte uidByte[4];
  } data1;
  int i;
  for (i=0;i<4;i++)
     data1.uidByte[i]=input[i];
  return data1.v;   
}
void sound(int duration,int freq)
{
  tone(buzzer, freq); // Send 1KHz sound signal...
  delay(duration);        // ...for 1 sec
  noTone(buzzer);     // Stop sound...
} 

void callback(char* topic, byte* payload, unsigned int length) {

  char result;
  result = payload[0];
  Serial.println(result);
  lcd.setCursor(0,1);
   
  if (result=='0')
  {
    Serial.println("invalid card");
    lcd.print("invalid card    ");
    sound(50,2000);
    delay(200);
    sound(50,2000);
    delay(200);    
    sound(50,2000);
    delay(200);    
  }
  if (result=='1')
  {
    Serial.println("No data");
    lcd.print("No data         ");
    sound(50,2500);
    delay(200);
    sound(50,2500);
    delay(200);    
    sound(50,2500);
    delay(200);            
  }
  if (result=='2')
  {
    Serial.println("OK              ");
    lcd.print("OK              ");    
    sound(50,1000);
  }
  if (result=='3')
  {
    Serial.println("Temp too high");
    lcd.print("Temp too high   ");
    sound(50,2500);
    delay(200);
    sound(50,2500);
    delay(200);    
    sound(50,2500);
    delay(200);            
  }  
  no=0;


}

//----------------------
void setup() 
{
  delay(200);
  Serial.begin(9600); // Initialize Serial to log output
 
  SPI.begin();      // Init SPI bus
  mfrc522.PCD_Init();   // Init MFRC522
  mfrc522.PCD_DumpVersionToSerial();  // Show details of PCD - MFRC522 Card Reader details
  Serial.println(F("Scan PICC to see UID, SAK, type, and data blocks..."));  

  
  lcd.init();                      // initialize the lcd 
  lcd.backlight();
  
  lcd.clear(); 
  lcd.setCursor(0,0);
  lcd.print("Wifi Connecting");
  WIFI_Connect();
  Serial.println("WiFi connected");  
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  MacAddress = GetWifiMac();
  Serial.println(MacAddress);
  MacAddress.toCharArray(mqtt_clientID,20); 
  client.setServer(mqtt_server, mqtt_port);  
  client.setCallback(callback);
  reconnect();
  no=0;
}

void loop() 
{

  String cmd;
  int i;
  boolean success;
  uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };  // Buffer to store the returned UID
  uint8_t uidLength;        // Length of the UID (4 or 7 bytes depending on ISO14443A card type)

  if (WiFi.status() != WL_CONNECTED)
  {   
    WIFI_Connect();    
  } 
  if (!client.connected()) {
    reconnect();
  }  
  client.loop(); 

 //read RFID

  if (no==0)
  {
    lcd.setCursor(0,0);
    lcd.print("Card Scanning   ");

    if(! mfrc522.PICC_IsNewCardPresent())
    {
      c=(c+1)%10;
      lcd.setCursor(15,0);
      lcd.print(String(c)); 
      return;  
    }
    if ( ! mfrc522.PICC_ReadCardSerial()) {
      lcd.setCursor(0,0);
      lcd.print("RFID reading error");  
      delay(500);  
      return;
    }
    sound(50,1000);
    mfrc522.PICC_DumpToSerial(&(mfrc522.uid)); 
    Serial.println(get_uid(mfrc522.uid.uidByte));
 //  lcd.setCursor(0,0);
 //  lcd.print(String(get_uid(mfrc522.uid.uidByte)));

   //----- MQTT: try max 5 times--------------
   no=1;
   cmd="{\"mac\":\""+MacAddress+"\",\"id\":\""+String(get_uid(mfrc522.uid.uidByte))+"\"}";
   cmd.toCharArray(msg,100);
  }
  if (no>0)
  {
    if ((no %5)==1)
    {
      client.publish(mqtt_publish_topic1,msg);  //retry
      Serial.println("mqtt publish");
    }
    no = no+1;
    if (no>15)
    {
        no =0;   //stop retry 
        Serial.println("mqtt failed. Please check connection");
    }
    delay(200);
  } 
}
