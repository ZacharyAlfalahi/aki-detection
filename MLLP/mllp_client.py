import logging
import os
import socket
import time
import joblib
from dotenv import load_dotenv

from decoder.decoder import process_message
from processor.processor import Processor
from metrics.metrics import MESSAGES_RECEIVED, MLLP_RECONNECTIONS, MESSAGE_PROCESSING_LATENCY

load_dotenv()

logger = logging.getLogger(__name__)

# MLLP Protocol Constants
MLLP_START_BLOCK = b"\x0b"
MLLP_END_BLOCK = b"\x1c"
MLLP_CARRIAGE_RETURN = b"\x0d"
RECV_BUFFER_SIZE = 1024

# Reconnection settings
INITIAL_RECONNECT_DELAY = 1  # seconds
MAX_RECONNECT_DELAY = 30  # seconds


def get_host_port(address):
    """Parse host and port from address string like 'localhost:8440'."""
    host, port_str = address.split(':')
    return host, int(port_str)


def recv_mllp_message(conn):
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


def send_ack(conn):
    """Send an ACK response over the connection."""
    ack = (
        "MSH|^~\\&|||||20240129093837||ACK|||2.5\r"
        "MSA|AA\r"
    )
    framed = MLLP_START_BLOCK + ack.encode() + MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN
    conn.sendall(framed)


def mllp_connection(mllp_address):
    """Establish MLLP connection with automatic reconnection and process messages."""
    # Load model and threshold once at connection start
    model_path = os.path.join(os.path.dirname(__file__), "..", "saved_model", "model.pkl")
    threshold_path = os.path.join(os.path.dirname(__file__), "..", "saved_model", "threshold.pkl")

    model = joblib.load(model_path)
    threshold = joblib.load(threshold_path)

    # Create single processor instance to maintain state across all messages
    patient_processor = Processor(model=model, threshold=threshold)

    host, port = get_host_port(mllp_address)
    reconnect_delay = INITIAL_RECONNECT_DELAY

    while True:  # Outer reconnection loop
        try:
            logger.info(f"Connecting to MLLP server at {host}:{port}")
            with socket.create_connection((host, port)) as conn:
                logger.info("Connected successfully")
                reconnect_delay = INITIAL_RECONNECT_DELAY  # Reset on success

                while True:  # Inner message loop
                    msg = recv_mllp_message(conn)
                    if msg is None:
                        logger.info("Connection closed by server, will reconnect")
                        MLLP_RECONNECTIONS.inc()
                        break

                    MESSAGES_RECEIVED.inc()

                    start_time = time.time()
                    clean_message = process_message(msg)
                    decision = patient_processor.process_event(event=clean_message)
                    latency_s = time.time() - start_time
                    MESSAGE_PROCESSING_LATENCY.observe(latency_s)

                    latency_ms = latency_s * 1000
                    if decision.page:
                        logger.warning(
                            f"AKI ALERT: Patient {decision.mrn} | "
                            f"Test time: {decision.timestamp} | "
                            f"Latency: {latency_ms:.2f}ms"
                        )
                    else:
                        logger.info(f"No page ({decision.reason}) | Latency: {latency_ms:.2f}ms")

                    send_ack(conn)

        except (ConnectionError, OSError, socket.error) as e:
            MLLP_RECONNECTIONS.inc()
            logger.error(f"MLLP connection error: {e}")

        logger.info(f"Reconnecting in {reconnect_delay}s...")
        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)
