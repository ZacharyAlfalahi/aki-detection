import logging
import os
import socket
import time
import joblib
from dotenv import load_dotenv

from decoder.decoder import process_message
from processor.processor import Processor

load_dotenv()

logger = logging.getLogger(__name__)

# MLLP Protocol Constants
MLLP_START_BLOCK = b"\x0b"
MLLP_END_BLOCK = b"\x1c"
MLLP_CARRIAGE_RETURN = b"\x0d"
RECV_BUFFER_SIZE = 1024


def get_host_port(address: str) -> tuple:
    """Parse host and port from address string like 'localhost:8440'."""
    host, port_str = address.split(':')
    return host, int(port_str)


def recv_mllp_message(conn) -> str | None:
    """Receive and decode an MLLP-framed message from the connection."""
    data = b""
    while True:
        chunk = conn.recv(RECV_BUFFER_SIZE)
        if not chunk:
            return None
        data += chunk
        if MLLP_END_BLOCK in data:
            break

    start = data.index(MLLP_START_BLOCK) + 1
    end = data.index(MLLP_END_BLOCK)
    return data[start:end].decode()


def send_ack(conn) -> None:
    """Send an ACK response over the connection."""
    ack = (
        "MSH|^~\\&|||||20240129093837||ACK|||2.5\r"
        "MSA|AA\r"
    )
    framed = MLLP_START_BLOCK + ack.encode() + MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN
    conn.sendall(framed)


def mllp_connection(mllp_address: str) -> None:
    """Establish MLLP connection and process messages.

    Args:
        mllp_address: URL of the MLLP server (e.g., 'http://localhost:8440')
    """
    # Load model and threshold once at connection start
    model_path = os.path.join(os.path.dirname(__file__), "..", "saved_model", "model.pkl")
    threshold_path = os.path.join(os.path.dirname(__file__), "..", "saved_model", "threshold.pkl")

    model = joblib.load(model_path)
    threshold = joblib.load(threshold_path)

    # Create single processor instance to maintain state across all messages
    patient_processor = Processor(model=model, threshold=threshold)

    host, port = get_host_port(mllp_address)
    logger.info(f"Connecting to MLLP server at {host}:{port}")

    with socket.create_connection((host, port)) as conn:
        logger.info("Connected successfully")
        while True:
            msg = recv_mllp_message(conn)
            if msg is None:
                logger.info("Connection closed by server")
                break

            start_time = time.time()
            clean_message = process_message(msg)
            decision = patient_processor.process_event(event=clean_message)
            latency_ms = (time.time() - start_time) * 1000

            if decision.page:
                logger.warning(
                    f"AKI ALERT: Patient {decision.mrn} | "
                    f"Test time: {decision.timestamp} | "
                    f"Latency: {latency_ms:.2f}ms"
                )
            else:
                logger.info(f"No page ({decision.reason}) | Latency: {latency_ms:.2f}ms")

            send_ack(conn)
