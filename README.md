# Helth-monitoring-and-management-system
a health monitoring and management system for an organization using RFID as personal identity

The whole system consists of two hardware devices and one software gateway. 

(a) The auto-thermometer can automatically measure the forehead temperature and sends the temperature value to the software gateway through the message queuing telemetry transport protocol (MQTT). 

(b) The software gateway stores the incoming message to the database. 

(c) The card screener can display the temperature value corresponding to the detetected UID by querying the software gateway also through MQTT. The status is displayed on the LCD and triggers a corresponding beep sound. In addition to entrance control, the data collected by the screener can also be used to find out the trace of a confirmed case during the incubation period.



