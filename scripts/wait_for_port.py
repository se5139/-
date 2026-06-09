from __future__ import annotations
import socket
import sys
import time

host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8520
timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 45
start = time.time()
while time.time() - start < timeout:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        if sock.connect_ex((host, port)) == 0:
            print('READY')
            sys.exit(0)
    time.sleep(1)
print('TIMEOUT')
sys.exit(1)
