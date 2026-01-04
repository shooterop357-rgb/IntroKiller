import time
import requests
import os
import sys
import logging

BOT_TOKEN = os.getenv("8161458476:AAH76ALCfc-zWa3Lwh8nitkjw82i8QJYat8")
if not BOT_TOKEN:
    print("BOT_TOKEN missing")
    sys.exit(1)

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="[WATCHDOG] %(asctime)s - %(message)s",
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "tg-watchdog/1.0"})

def api_call(method, params=None, timeout=10):
    try:
        r = SESSION.get(f"{API}/{method}", params=params, timeout=timeout)
        return r.json()
    except Exception:
        return None

def delete_webhook():
    r = api_call("deleteWebhook", {"drop_pending_updates": True})
    logging.info("deleteWebhook → %s", r)

def aggressive_poll():
    """
    Drain updates so other pollers get conflicts / empty updates
    """
    offset = -1
    while True:
        r = api_call(
            "getUpdates",
            {
                "offset": offset,
                "limit": 100,
                "timeout": 0,
            },
            timeout=5,
        )

        if not r or not r.get("ok"):
            time.sleep(2)
            continue

        updates = r.get("result", [])
        if updates:
            offset = updates[-1]["update_id"] + 1
            logging.info("Drained %d updates", len(updates))
        else:
            logging.info("No updates (holding poll)")

        time.sleep(1)

def watchdog():
    logging.info("Watchdog started")
    delete_webhook()   # webhook users ko hatao

    while True:
        me = api_call("getMe")
        if not me or not me.get("ok"):
            logging.warning("Token/API unstable, retrying...")
            time.sleep(5)
            continue

        logging.info("Bot alive: %s", me["result"]["username"])

        try:
            aggressive_poll()
        except Exception:
            logging.warning("Poll loop crashed, restarting...")
            time.sleep(2)

if __name__ == "__main__":
    watchdog()
