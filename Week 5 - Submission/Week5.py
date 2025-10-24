#imports
from network import WLAN  
import time               
import socket
import machine
import cryptolib
from machine import Pin, PWM, ADC
import json

# WiFi in station mode
wifi = WLAN(WLAN.IF_STA)
wifi.active(True)

# WiFi credentials
ssid = 'REDACTED'
password = 'REDACTED'

# Connect to network
wifi.connect(ssid, password)
time.sleep(5)
wifi_status = 3

# Check if the connection is successful
if wifi_status != 3:
    print("Wi-Fi couldn't connect")
else:
    #DNS test
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

# Port for HTTP server
port_number = 80

if not connect(wifi, ssid, password):
    print("Wifi couldn't connect")
else:
    # Create TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )
    s.bind(('0.0.0.0', port_number))
    s.listen(1)
    
    # Display connection information
    ip = wifi.ifconfig()[0]
    print(f'Listening on IP {ip}, port {port_number}')

    # Set LED on GPIO pin 0 with PWM
    led = PWM(Pin(0), freq=50, duty_u16=0)
    
    current_brightness = 0.0
    
    # Function to change LED brightness
    def change_led(led_obj, brightness):
        assert 0 <= brightness <= 1 
        minimum, maximum = 0, 55000  
        diff = maximum - minimum
        duty_cycle = (brightness / 1) * diff + minimum
        print(f"Setting duty cycle to: {duty_cycle}")  
        led_obj.duty_u16(int(duty_cycle))
        return brightness
    
    #read temperature
    temp_sensor = ADC(4)
    
    def read_temp():
        global temp_sensor
        
        value = temp_sensor.read_u16()
        voltage = value * (3.3 / 2 ** 16)
        temperature = 27 - (voltage - 0.706) / .001721
        
        return temperature
    
    print(f'The temperature is {read_temp()} degrees')

    #timer
    timer = machine.Timer()
    timer_message = "Timer initialized"
    
    def timer_callback(t):
        global timer_message
        timer_message = "Hello, World!"
        print('Hello, World!')

    timer.init(freq=1, mode=machine.Timer.PERIODIC, callback=timer_callback)
    
    # encryption key and IV
    iv = b'hey!'
    key = b'secret!'
    data = b'Hello, World!'

    # pad data to 16 bytes
    def pad_128(data):
        output = data[:]
        # Keep adding data until we reach 16 bytes
        while len(output) < 16:
            output += data
       
        # If exactly 16 bytes, return as is
        if len(output) == 16:
            return output
       
        # modulo trimming
        return output[:-(len(output) % 16)]
    
    # Pad all inputs to 128 bits (16 bytes)
    padded_key = pad_128(key)
    padded_iv = pad_128(iv)
    padded_data = pad_128(data)

    # The 2 means we want to use CBC mode
    # Create cipher object for encryption
    cipher = cryptolib.aes(padded_key, 2, padded_iv)

    # Encrypt the data
    ciphertext = cipher.encrypt(padded_data)

    # Display results
    print(ciphertext)
    
    send data BEFORE starting HTTP server
    print("Connecting to laptop...")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    laptop_ip = '172.20.10.3'  
    laptop_port = 8000
    
    try:
        client_socket.connect((laptop_ip, laptop_port))
        
        # send encrypted data
        client_socket.send(ciphertext)
        time.sleep(0.5)
        
        # send temperature data
        for i in range(5):
            temperature = read_temp()
            message = f"Temperature: {temperature:.2f}C\n"
            client_socket.send(message.encode('utf-8'))
            time.sleep(2)
        
        client_socket.close()
        print("Finished sending data to laptop")
    except Exception as e:
        print(f"Failed to connect to laptop: {e}")
    
    # Main server loop
    while True:
        # accept incoming connection
        cxn, addr = s.accept()
        print(f'Connected to {addr}')
        
        # Receive data from client
        data = b''
        while True:
            chunk = cxn.recv(1024)
            if not chunk:
                break
            data += chunk
            # Check for complete request
            if b'\r\n\r\n' in data:
                # check for body
                header_end = data.find(b'\r\n\r\n')
                headers = data[:header_end].decode()
                
                # Check for Content-Length
                if b'Content-Length:' in data[:header_end]:
                    for line in headers.split('\r\n'):
                        if line.startswith('Content-Length:'):
                            content_length = int(line.split(':')[1].strip())
                            body_start = header_end + 4
                            # Keep reading until we have the full body
                            while len(data) < body_start + content_length:
                                chunk = cxn.recv(1024)
                                if not chunk:
                                    break
                                data += chunk
                            break
                break
        
        data = data.decode()
        print(f'Received ({len(data)} bytes): {data}')
        
        # Success status
        status_line = "HTTP/1.0 200 OK\r\n"
        brightness_output = "OK"
        request_value = "false"
        
        try:
            request_line = data.split("\r\n")[0]
            parts = request_line.split(" ")
            method = parts[0]
            path = parts[1]
            
            print(f"Method: {method}, Path: {path}")
            
            # Handle POST requests to /rest/led
            if method == "POST" and path == "/rest/led":
                body_start = data.find("\r\n\r\n")
                if body_start != -1:
                    json_body = data[body_start + 4:]
                    print(f"JSON body: '{json_body}'")
                    
                    # Parse JSON
                    parsed = json.loads(json_body)
                    print(f"Parsed JSON: {parsed}")
                    
                    brightness = float(parsed["brightness"])
                    print(f"Brightness value: {brightness}")
                    
                    if 0.0 <= brightness <= 1.0:
                        current_brightness = change_led(led, brightness)
                        brightness_output = f"Brightness set to {brightness*100:.1f}%"
                    else:
                        status_line = "HTTP/1.0 400 Bad Request\r\n"
                        brightness_output = "Error: Brightness out of range (0.0-1.0)"
                else:
                    status_line = "HTTP/1.0 400 Bad Request\r\n"
                    brightness_output = "Error: No JSON body found"
                    
            # Handle GET requests to /led?brightness=X
            elif method == "GET" and path.startswith("/led?brightness="):
                brightness_str = path.split("=")[1]
                print(f"GET brightness string: {brightness_str}")
                
                brightness = float(brightness_str)
                
                if 0.0 <= brightness <= 1.0:
                    current_brightness = change_led(led, brightness)
                    brightness_output = f"Brightness set to {brightness*100:.1f}%"
                else:
                    status_line = "HTTP/1.0 400 Bad Request\r\n"
                    brightness_output = "Error: Brightness out of range"
            else:
                status_line = "HTTP/1.0 404 Not Found\r\n"
                brightness_output = f"Error: Unknown endpoint {method} {path}"
        
        except Exception as e:
            status_line = "HTTP/1.0 500 Internal Server Error\r\n"
            brightness_output = f"Error: {str(e)}"
            print(f"Exception occurred: {e}")
            import sys
            sys.print_exception(e)
        
        json_response = f'{{"brightness": {current_brightness}, "message": "{brightness_output}", "request": "{request_value}"}}'
        
        # full HTTP response
        response = status_line
        response += "Content-Type: application/json\r\n"
        response += f"Content-Length: {len(json_response)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += json_response
        
        print(f"Sending response")
        cxn.sendall(response.encode())
        time.sleep(0.5)
        print("Closing the connection")
        cxn.close()
