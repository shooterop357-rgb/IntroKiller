import time
import requests
import os
import sys
import logging

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("BOT_TOKEN missing")
    sys.exit(1)

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="[WATCHDOG] %(asctime)s - %(message)s",
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "tg-watchdog/2.0"})

def api_call(method, params=None, timeout=15):
    try:
        r = SESSION.post(f"{API}/{method}", json=params, timeout=timeout)
        return r.json()
    except Exception:
        return None

def delete_webhook_hard():
    r = api_call(
        "deleteWebhook",
        {
            "drop_pending_updates": True
        }
    )
    logging.info("Webhook nuked → %s", r)

def aggressive_poll_lock():
    """
    HARD LOCK:
    - allowed_updates=[]
    - offset pushed to extreme
    - long poll holds connection
    """
    offset = 2**31 - 1  # jump beyond all updates

    while True:
        r = api_call(
            "getUpdates",
            {
                "offset": offset,
                "limit": 1,
                "timeout": 50,
                "allowed_updates": [],  # RECEIVE NOTHING
            },
            timeout=60,
        )

        if not r or not r.get("ok"):
            logging.warning("getUpdates failed, retrying lock...")
            time.sleep(2)
            continue

        # Even if Telegram sends something (rare), discard it
        updates = r.get("result", [])
        if updates:
            offset = updates[-1]["update_id"] + 1
            logging.info("Force-drained %d update(s)", len(updates))
        else:
            logging.info("Holding update lock (silent)")

def watchdog():
    logging.info("WATCHDOG ONLINE")
    delete_webhook_hard()

    while True:
        me = api_call("getMe")
        if not me or not me.get("ok"):
            logging.warning("API unstable, retrying...")
            time.sleep(5)
            continue

        logging.info("Bot locked: @%s", me["result"]["username"])

        try:
            aggressive_poll_lock()
        except Exception:
            logging.warning("Lock crashed, restarting...")
            time.sleep(2)

if __name__ == "__main__":
    watchdog()
