#imports
from network import WLAN  
import time               
import socket             
from machine import Pin, PWM

# WiFi in station mode
wifi = WLAN(WLAN.IF_STA)
wifi.active(True)

# WiFi credentials
ssid = 'iPhone :)'
password = 'N/A'

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
    
    # Function to change LED brightness
    def change_led(led_obj, brightness):
        assert 0 <= brightness <= 1 
        minimum, maximum = 0, 55000  
        diff = maximum - minimum
        duty_cycle = (brightness / 1) * diff + minimum
        print(duty_cycle)  
        led_obj.duty_u16(int(duty_cycle))
        return brightness
    
 
 
 
    # Main server loop
    while True:
        # Accept incoming connection
        cxn, addr = s.accept()
        print(f'Connected to {addr}')
        
        # Receive data from client
        data = cxn.recvfrom(200)[0].decode()
        print(f'Received ({len(data)} bytes): {data}')
        
        # Success status
        status_line = "HTTP/1.0 200 OK\r\n"
        
        try:
            request_line = data.split("\r\n")[0]
            path = request_line.split(" ")[1] 
            
            # determining if the URL is of the required schema
            if path.startswith("/led?brightness="):
                brightness_str = path.split("=")[1]
                
                try:
                    # reading the value of the floating point number passed, and validating it
                    brightness = float(brightness_str)
                    if 0.0 <= brightness <= 1.0:
                        change_led(led, brightness)
                        brightness_output = f"Brightness set to {brightness*100:.1f}%"
                    else:
                        raise ValueError("Out of range")
                except ValueError:
                    
                    # returning a 404 if the input is incorrect/invalid
                    status_line = "HTTP/1.0 404 Not Found\r\n"
                    brightness_output = "Error: Invalid brightness value!"
            else:   
                status_line = "HTTP/1.0 404 Not Found\r\n"
                brightness_output = "Error: Malformed path!"
    
        except ValueError as e:
            status_line = "HTTP/1.0 404 Not Found\r\n"
            brightness_output = f"Error: {e}"
 
 
 
        # responding to a HTTP request in a way that the browser accepts
        response = status_line
        response += "Content-Type: text/html\r\n"
        response += "\r\n"
        response += "<p>Hello</p>"
        response += f"Brightness Output: {brightness_output}"
        cxn.sendall(response.encode())
        time.sleep(2)
        print("Closing the connection") # Close the connection
        cxn.close()
