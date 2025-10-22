#imports
from network import WLAN  
import time               
import socket             
from machine import Pin, PWM
import json

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
    
    # Main server loop
    while True:
        # Accept incoming connection
        cxn, addr = s.accept()
        print(f'Connected to {addr}')
        
        # Receive data from client - keep receiving until we have everything
        data = b''
        while True:
            chunk = cxn.recv(1024)
            if not chunk:
                break
            data += chunk
            # Check if we have the complete request
            if b'\r\n\r\n' in data:
                # For POST, check if we have the body too
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
                # Find the JSON body (after \r\n\r\n)
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
        
        # Build full HTTP response
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