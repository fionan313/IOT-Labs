import umqtt.robust as umqtt
from network import WLAN
import time               
import socket
import machine
import cryptolib
from machine import Pin, PWM, ADC
import json

# Assuming that you connect to the internet as normal...
print("Starting program")

# Set up the fan on GPIO 16
fan = Pin(16, Pin.OUT)
fan.value(0)

TEMP_THRESHOLD = 30.0  # Turn fan on above 30°C

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


HOSTNAME = '172.20.10.8'
PORT = 8080
TOPIC = 'temp/pico'

mqtt = umqtt.MQTTClient(
    client_id = b'subscribe',
    server = HOSTNAME.encode(),
    port = PORT,
    keepalive = 7000 # seconds
)

def callback(topic, message):
    # Ignore messages that are not part of the temp/pico topic
    if topic.decode() != 'temp/pico':
        return
    
    print(f'I received the message "{message}" for topic "{topic}"')
    
    try:
        temp = float(message.decode())
        print(f"Temperature: {temp}°C")
        
        if temp > TEMP_THRESHOLD:
            fan.value(1)  # Turn fan ON
            print("Fan ON")
        else:
            fan.value(0)  # Turn fan OFF
            print("Fan OFF")
    except ValueError:
        print("Error")

mqtt.connect()

# Assuming that you have the temperature as an int or a
# float in a variable called 'temp':
                
#timer
timer = machine.Timer()
timer_message = "Timer initialized"

def timer_callback(t):
    mqtt.set_callback(callback)
    mqtt.subscribe(TOPIC)
    mqtt.wait_msg() # Blocking wait
                # -- use .check_msg() for non-blocking

timer.init(freq=1, mode=machine.Timer.PERIODIC, callback=timer_callback)
