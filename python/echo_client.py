# echo_client.py

import socket

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    sentence = input('Input lowercase sentence:')
    s.sendall(sentence.encode())
    modified_data = s.recv(1024)

print(f"Received {modified_data.decode()}")