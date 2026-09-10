# echo_server.py

import socket

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    
    # Just want to see the socket info
    print('The server is (ip, port no.): ', s.getsockname())
    print('The server is ready to receive')

    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if data:
                print(f"Received {data.decode()}")
            if not data:
                break
            conn.sendall(data.upper())

