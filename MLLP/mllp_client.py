import socket
from decoder.decoder import process_message
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
import time

load_dotenv()

MLLP_ADDRESS = os.environ.get("MLLP_ADDRESS")

def get_host_port(address):
    parsed = urlparse(address)
    host = parsed.hostname
    port = parsed.port
    return host, port

def recv_mllp_message(conn):
    SB = b"\x0b"
    EB = b"\x1c"
    CR = b"\x0d"

    data = b""
    while True:
        chunk = conn.recv(1024)
        if not chunk:
            return None
        data += chunk
        if EB in data:
            break

    start = data.index(SB) + 1
    end = data.index(EB)
    return data[start:end].decode()

def send_ack(conn):
    SB = b"\x0b"
    EB = b"\x1c"
    CR = b"\x0d"
    
    ack = (
        "MSH|^~\\&|||||20240129093837||ACK|||2.5\r"
        "MSA|AA\r"
    )
    framed = SB + ack.encode() + EB + CR
    conn.sendall(framed)


def mllp_connection(mllp_address):
    host, port = get_host_port(mllp_address)
    with socket.create_connection((host, port)) as conn:
        while True:
            msg = recv_mllp_message(conn)
            if msg == None:
                break
            start_time = time.time()
            clean_message = process_message(msg)
            print(clean_message.get("message_type"))

            # INSERT PROCESSING HERE

            process_length = time.time() - start_time

            send_ack(conn)