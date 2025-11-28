import umqtt.robust as umqtt
from network import WLAN
import time               
import socket
import machine
import cryptolib
from machine import Pin, PWM, ADC, RTC
import uprotobuf

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
password = ''

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

# RTC for time tracking
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
        from temp_schema_upb2 import TempMessage, Time
        
        dt = rtc.datetime()
        message = TempMessage()
        message.pub_id = PUB_IDENT
        message.temperature = read_temp()
        message.time.hour = dt[4]
        message.time.minute = dt[5]
        message.time.second = dt[6]
        
        payload = message.serialize()
        mqtt.publish(TOPIC, payload)
        print(f'Published: pub_id={PUB_IDENT}, temp={message.temperature}, time={dt[4]}:{dt[5]}:{dt[6]}')
    
    timer.init(freq=1, mode=machine.Timer.PERIODIC, callback=timer_callback)

# SUBSCRIBER MODE
elif OUTPUT_PIN is not None and PUB_IDENT is None:
    print("Running as SUBSCRIBER")
    
    from temp_schema_upb2 import TempMessage, Time
    
    # Set up the fan
    fan = Pin(OUTPUT_PIN, Pin.OUT)
    fan.value(0)
    
    TEMP_THRESHOLD = 25.0
    
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
        
        print(f'Received message')
        
        try:
            data = TempMessage()
            data.parse(message)
            
            pub_id = data.pub_id._value
            temp = data.temperature._value
            timestamp = data.time.hour._value * 3600 + data.time.minute._value * 60 + data.time.second._value
            
            # Store data from this publisher
            publishers_data[pub_id] = {
                'temp': temp,
                'time': timestamp
            }
            
            # Calculate average from publishers active in last 10 minutes
            current_time = get_time_seconds()
            valid_temps = []
            
            # Remove old publishers
            to_remove = []
            for pid, pdata in publishers_data.items():
                if current_time - pdata['time'] <= 600:  # 10 minutes = 600 seconds
                    valid_temps.append(pdata['temp'])
                else:
                    to_remove.append(pid)
            
            for pid in to_remove:
                del publishers_data[pid]
            
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