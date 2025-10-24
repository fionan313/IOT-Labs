import socket
from Crypto.Cipher import AES

port_number_pc = 8000

# Create socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind and listen for connetions
s.bind(('0.0.0.0', port_number_pc))
s.listen(1)

print(f"Listening on port {port_number_pc}...")
print("Waiting for Pico to connect...")

# Accept connection from Pico
conn, addr = s.accept()
print(f"Connected by {addr}")

# Pad data to 16 bytes (128 bits) for AES encryption
def pad_128(data):
    output = data[:]
    while len(output) < 16:
        output += data
    if len(output) == 16:
        return output
    return output[:-(len(output) % 16)]

# encryption key and IV
key = pad_128(b"secret!")  
iv = pad_128(b"hey!")  

# cipher object for decryption
cipher = AES.new(key, AES.MODE_CBC, iv)

print("Receiving data from Pico...")


try:
    # get first chunk
    first_chunk = conn.recv(1024)
    
    if len(first_chunk) == 16:
        print("Received encrypted data")
        plaintext = cipher.decrypt(first_chunk)
        print(f"Decrypted: {plaintext}")
    
    print("\nReceiving temperature data:")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        print(data.decode('utf-8'), end='')

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
    s.close()
    print("\nConnection closed")