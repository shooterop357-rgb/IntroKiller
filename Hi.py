import time
import requests
import os
import sys

BOT_TOKEN = os.getenv("8161458476:AAH76ALCfc-zWa3Lwh8nitkjw82i8QJYat8")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

OWNER_ID = 5436530930   # apni TG ID

def watchdog():
    while True:
        try:
            r = requests.get(f"{API}/getMe", timeout=5)
            if not r.ok:
                time.sleep(3)
                continue

            # aggressive getUpdates (conflict creator)
            requests.get(
                f"{API}/getUpdates",
                params={
                    "offset": -1,
                    "timeout": 0,
                    "limit": 1
                },
                timeout=3
            )

        except Exception:
            pass

        time.sleep(5)  # repeat forever
