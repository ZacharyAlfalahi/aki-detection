import requests
import os
from dotenv import load_dotenv

load_dotenv()

PAGER_ADDRESS = os.environ.get("PAGER_ADDRESS")

def page_hospital(mrn, time, pager_url=PAGER_ADDRESS):
    payload = f"{mrn},{time}"

    if not pager_url.startswith(('http://', 'https://')):
        pager_url = f"http://{pager_url}"

    r = requests.post(
        f"{pager_url.rstrip('/')}/page",
        data=payload, 
        headers={"Content-Type": "text/plain"},
        timeout=2,
    )
    r.raise_for_status()
