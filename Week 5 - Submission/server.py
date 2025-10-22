import requests
import sys
import cryptolib
import socket
from Crypto.Cipher import AES

# The API endpoint
#url = "http://172.20.10.4/rest/led"

# Data to be sent
#data = {
    #"brightness": sys.argv[2],
    #"request": sys.argv[3],
    #"body": "is tea."
#}

# A POST request to the API
#response = requests.post(url, json=data)

port_number_pc = 81

# Create socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(('0.0.0.0', port_number_pc))
s.listen(1)

print("Waiting for Pico to connect...")
conn, addr = s.accept()
print(f"Connected by {addr}")

# Receive and display temperature data
while True:
    data = conn.recv(1024)
    if not data:
        break
    print(data.decode('utf-8'), end='')

conn.close()

# AES Decryption setup
key = b"secret!"  
iv = b"hey!"  

cipher = AES.new(key, AES.MODE_CBC, iv)

# Decrypt ciphertext
ciphertext = conn.recv(1024)
plaintext = cipher.decrypt(ciphertext)

print(plaintext)