import umqtt.robust as umqtt
from network import WLAN
import time               
import socket
import machine
import cryptolib
from machine import Pin, PWM, ADC, RTC
import json

print("Starting program...")


BROKER_IP = '172.20.10.8'
TOPIC = 'temp/pico'
OUTPUT_PIN = None  
PUB_IDENT = 'pico_001'  

# WiFi in station mode
wifi = WLAN(WLAN.IF_STA)
wifi.active(True)

# WiFi credentials
ssid = 'iPhone :)'
password = 'AppleInternal2024!'

# Connect to network
wifi.connect(ssid, password)
time.sleep(5)

# Check if the connection is successful
if wifi.status() != 3:
    print("Wi-Fi couldn't connect")
else:
    #perform DNS test
    tudublin_dns = socket.getaddrinfo("tudublin.ie", 443)
    tudublin_ip = tudublin_dns[0][-1][0]
    
    print(f"The IP address for the TU Dublin website is {tudublin_ip}")

# Initialize RTC for time tracking
rtc = RTC()

def get_time_seconds():
    dt = rtc.datetime()
    return dt[4] * 3600 + dt[5] * 60 + dt[6]

PORT = 8080

# PUBLISHER 
if PUB_IDENT is not None and OUTPUT_PIN is None:
    print("Running as PUBLISHER")
    
    mqtt = umqtt.MQTTClient(
        client_id=PUB_IDENT.encode(),
        server=BROKER_IP.encode(),
        port=PORT,
        keepalive=7000
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
    
    #timer
    timer = machine.Timer()
    
    def timer_callback(t):
        payload = json.dumps({
            'pub_id': PUB_IDENT,
            'temperature': read_temp(),
            'timestamp': get_time_seconds()
        })
        mqtt.publish(TOPIC, payload.encode())
        print(f'Published: {payload}')
    
    timer.init(freq=1, mode=machine.Timer.PERIODIC, callback=timer_callback)

# SUBSCRIBER MODE
elif OUTPUT_PIN is not None and PUB_IDENT is None:
    print("Running as SUBSCRIBER")
    
    # Set up the fan
    fan = Pin(OUTPUT_PIN, Pin.OUT)
    fan.value(0)
    
    TEMP_THRESHOLD = 30.0
    
    # Track publishers: {pub_id: {'temp': float, 'time': int}}
    publishers_data = {}
    
    mqtt = umqtt.MQTTClient(
        client_id = b'subscribe',
        server = BROKER_IP.encode(),
        port = PORT,
        keepalive = 7000
    )
    
    def callback(topic, message):
        if topic.decode() != TOPIC:
            return
        
        print(f'Received message: {message}')
        
        try:
            data = json.loads(message.decode())
            pub_id = data['pub_id']
            temp = data['temperature']
            
            # Store data from this publisher
            publishers_data[pub_id] = {
                'temp': temp,
                'time': get_time_seconds()
            }
            
            # Calculate average from publishers active in last 10 minutes
            current_time = get_time_seconds()
            valid_temps = []
            
            for pid, pdata in publishers_data.items():
                if current_time - pdata['time'] <= 600:  # 10 minutes = 600 seconds
                    valid_temps.append(pdata['temp'])
            
            if valid_temps:
                avg_temp = sum(valid_temps) / len(valid_temps)
                print(f"Average temp from {len(valid_temps)} publisher(s): {avg_temp}°C")
                
                if avg_temp > TEMP_THRESHOLD:
                    fan.value(1)
                    print("Fan ON")
                else:
                    fan.value(0)
                    print("Fan OFF")
            
        except Exception as e:
            print(f"Error: {e}")
    
    mqtt.connect()
    mqtt.set_callback(callback)
    mqtt.subscribe(TOPIC)
    
    #timer
    timer = machine.Timer()
    
    def timer_callback(t):
        mqtt.check_msg()
    
    timer.init(freq=1, mode=machine.Timer.PERIODIC, callback=timer_callback)

else:
    print("ERROR: Set either PUB_IDENT or OUTPUT_PIN, not both")

while True:
    time.sleep(1)
