import requests
import sys
import socket
#from Crypto.Cipher import AES

# The API endpoint
url = "http://172.20.10.4/rest/led"

# Data to be sent
data = {
    "brightness": sys.argv[2],
    "request": sys.argv[3],
    "body": "is tea."
}

# A POST request to the API
response = requests.post(url, json=data)

# Print the response
print(response.json())