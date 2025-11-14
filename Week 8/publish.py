import umqtt.robust as umqtt
from network import WLAN
import time               
import socket
import machine
import cryptolib
from machine import Pin, PWM, ADC
import json

print("Starting program...")

# WiFi in station mode
wifi = WLAN(WLAN.IF_STA)
wifi.active(True)

# WiFi credentials
ssid = 'iPhone :)'
password = 'AppleInternal2024!'

# Connect to network
wifi.connect(ssid, password)
time.sleep(5)
wifi_status = 3

# Check if the connection is successful
if wifi_status != 3:
    print("Wi-Fi couldn't connect")
else:
    #perform DNS test
    tudublin_dns = socket.getaddrinfo("tudublin.ie", 443)
    tudublin_ip = tudublin_dns[0][-1][0]
    
    print(f"The IP address for the TU Dublin website is {tudublin_ip}")

# Function for connecting to network
def connect(wifi_obj, ssid, password, timeout=10):
    wifi_obj.connect(ssid, password)
    
    while timeout > 0:
        if wifi_obj.status() == 3: 
            return True
        time.sleep(1)
        timeout -= 1
        
    return False

# Assuming that you connect to the internet as normal...
HOSTNAME = '172.20.10.8'
PORT = 8080
TOPIC = 'temp/pico'

mqtt = umqtt.MQTTClient(
    client_id=b'publish',
    server=HOSTNAME.encode(),
    port=PORT,
    keepalive=7000  # seconds
)

mqtt.connect()

#read temperature
temp = ADC(4)

def read_temp():
    global temp
    
    value = temp.read_u16()
    voltage = value * (3.3 / 2 ** 16)
    temperature = 27 - (voltage - 0.706) / .001721
    
    return temperature

# Assuming that you have the temperature as an int or a
# float in a variable called 'temp':


#timer
timer = machine.Timer()
timer_message = "Timer initialized"

def timer_callback(t):
    mqtt.publish(TOPIC, str(read_temp()).encode())
    print(f'The temperature is {read_temp()} degrees')

timer.init(freq=1, mode=machine.Timer.PERIODIC, callback=timer_callback)
