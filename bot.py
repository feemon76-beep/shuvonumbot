import telebot
import requests
import json
import pycountry
import threading
import time
import re
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ---------------- CONFIG ----------------
BOT_TOKEN = "8510677584:AAF476dQapgxGmi5nkJPt0euc_JDY8A4wSE"
ADMIN_ID = "6136815573" # তোর দেওয়া আইডি সেট করলাম
ADMIN_USERNAME = "@PRINCE_SHUVO_75"
OTP_GROUP_LINK = "https://t.me/tem_withh"
API_KEY = "M_SX44INH5S"
API_BASE = "https://stexsms.com/mapi/v1/public"
# ----------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)
user_active_sessions = {}

def get_auto_flag(country_name):
    try:
        manual_flags = {"Ivory Coast": "🇨🇮", "Bangladesh": "🇧🇩", "Guinea": "🇬🇳", "Nepal": "🇳🇵"}
        if country_name in manual_flags: return manual_flags[country_name]
        country = pycountry.countries.search_fuzzy(country_name)[0]
        return "".join(chr(127397 + ord(c)) for c in country.alpha_2)
    except: return "🚩"

def fetch_single_number(rng):
    try:
        url = f"{API_BASE}/getnum/number"
        headers = {"mapikey": API_KEY, "Content-Type": "application/json"}
        payload = {"range": rng, "is_national": False, "remove_plus": False}
        res = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15).json()
        return res.get("data", {})
    except: return {}

def check_otp_from_list(target_number):
    try:
        url = f"{API_BASE}/numsuccess/info"
        headers = {"mapikey": API_KEY}
        res = requests.get(url, headers=headers, timeout=10).json()
        if res.get("meta", {}).get("status") == "success":
            otps = res.get("data", {}).get("otps", [])
            clean_target = re.sub(r'\D', '', str(target_number))
            for item in otps:
                clean_api_num = re.sub(r'\D', '', str(item.get("number")))
                if clean_target in clean_api_num:
                    full_otp_text = str(item.get("otp"))
                    # এখানে লজিক চেঞ্জ করলাম: মেসেজ থেকে শুধু ৪-৮ ডিজিটের সংখ্যাটা নিবে
                    otp_only = re.findall(r'\d{4,8}', full_otp_text)
                    if otp_only:
                        return otp_only[0] # শুধু কোডটা পাঠাবে
                    return full_otp_text
    except: pass
    return None

@bot.message_handler(commands=['start'])
def start(msg):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📱 Get Number"), KeyboardButton("👨‍💻 ADMIN SUPPORT"))
    bot.send_message(msg.chat.id, "👋 WELCOME SHUVO!\n\n🧭 PLEASE SELECT A BUTTON BELOW:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👨‍💻 ADMIN SUPPORT")
def admin_support(msg):
    bot.send_message(msg.chat.id, f"👨‍💻 **ADMIN SUPPORT**\n\nযোগাযোগ করুন: {ADMIN_USERNAME}", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📱 Get Number")
def ask_range(msg):
    send_msg = bot.send_message(msg.chat.id, "🎯 আপনার টার্গেট রেঞ্জটি লিখুন:", parse_mode="Markdown")
    bot.register_next_step_handler(send_msg, process_range)

def process_range(msg):
    rng = msg.text.strip()
    fetch_and_send_numbers(msg.chat.id, rng)

def fetch_and_send_numbers(chat_id, rng, message_id=None):
    try:
        data1 = fetch_single_number(rng)
        data2 = fetch_single_number(rng)
        num1 = data1.get("full_number") or data1.get("number")
        num2 = data2.get("full_number") or data2.get("number")
        country = data1.get("country") or data2.get("country") or "Unknown"
        flag = get_auto_flag(country)

        if num1 or num2:
            d_num1 = str(num1).replace('+', '') if num1 else "⚠️ No stock"
            d_num2 = str(num2).replace('+', '') if num2 else "⚠️ No stock"
            session_id = time.time()
            user_active_sessions[chat_id] = {
                'session_id': session_id, 'range': rng, 'num1': d_num1, 'num2': d_num2,
                'country': country, 'flag': flag, 'found_ids': []
            }

            update_text = (
                f"╔══════════════════╗\n   {flag} FACEBOOK SERVICE\n╚══════════════════╝\n\n"
                f"🌍 {country} {flag}\n"
                f"┌──────────────────┐\n"
                f"📞 Num ①: `{d_num1}`\n"
                f"📞 Num ②: `{d_num2}`\n"
                f"└──────────────────┘\n\n"
                f"╔══════════════════╗\n  🔥 PRINCE SHUVO BOT 🔥\n╚══════════════════╝"
            )

            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton(text="🔄 Get New Numbers", callback_data="change_direct"))
            kb.row(InlineKeyboardButton(text="⚙️ Change Search Range", callback_data="change_range_request"))
            kb.row(InlineKeyboardButton(text="📢 View OTP Inbox ↗️", url=OTP_GROUP_LINK))
            
            if message_id: bot.edit_message_text(update_text, chat_id, message_id, reply_markup=kb, parse_mode="Markdown")
            else: bot.send_message(chat_id, update_text, reply_markup=kb, parse_mode="Markdown")
            
            threading.Thread(target=auto_otp_worker, args=(chat_id, session_id)).start()
        else:
            bot.send_message(chat_id, "⚠️ এই রেঞ্জে নম্বর পাওয়া যায়নি।")
    except Exception as e: print(f"Error: {e}")

@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    if call.data == "change_direct":
        rng = user_active_sessions.get(chat_id, {}).get('range')
        if rng: fetch_and_send_numbers(chat_id, rng, call.message.message_id)
    elif call.data == "change_range_request":
        msg = bot.send_message(chat_id, "🖋 নতুন রেঞ্জটি লিখুন:")
        bot.register_next_step_handler(msg, process_range)

def auto_otp_worker(chat_id, session_id):
    while True:
        data = user_active_sessions.get(chat_id)
        if not data or data.get('session_id') != session_id: break
            
        nums = [data.get('num1'), data.get('num2')]
        for current_num in nums:
            if current_num != "⚠️ No stock":
                otp = check_otp_from_list(current_num)
                # একই কোড বারবার পাঠাবে না
                if otp and f"{current_num}_{otp}" not in data['found_ids']:
                    data['found_ids'].append(f"{current_num}_{otp}")
                    otp_msg = (
                        f"🌍 {data['country']} {data['flag']}\n\n"
                        f"📞 Num: {current_num}\n\n"
                        f"📩 OTP: `{otp}`"
                    )
                    bot.send_message(chat_id, otp_msg, parse_mode="Markdown")
        time.sleep(5)

if __name__ == "__main__":
    bot.infinity_polling()