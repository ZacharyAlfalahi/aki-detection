import os
from dotenv import load_dotenv
from MLLP.mllp_client import mllp_connection

load_dotenv()

PAGER_ADDRESS = os.environ.get("PAGER_ADDRESS")
MLLP_ADDRESS = os.environ.get("MLLP_ADDRESS")

def main():
    if not MLLP_ADDRESS:
        raise ValueError("MLLP_ADDRESS environment variable not set")
    mllp_connection(MLLP_ADDRESS)

if __name__ == "__main__":
    main()