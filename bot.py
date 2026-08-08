import re
import os
import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "8738544813:AAG7WMbdgN7xXZwNGKrJrxCv6PBc_2c-0fA")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6136815573"))

bot = telebot.TeleBot(TOKEN)

user_states = {}
available_numbers = {"Facebook": {"Tanzania": []}}
user_active_numbers = {} 

session = requests.Session()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    first_name = message.from_user.first_name or ""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📱 GET NUMBER"),
        KeyboardButton("🔍 OTP SEARCH"),
    )
    
    if message.from_user.id == ADMIN_ID:
        markup.add(KeyboardButton("⚙️ ADMIN"))
        
    bot.send_message(message.chat.id, f"👋 Welcome {first_name}", reply_markup=markup)

def login_and_get_otp():
    """✅ Simple login + get OTP"""
    try:
        # Direct simple login - no complexity
        print("\n🔐 Attempting login...")
        
        # Method 1: Try direct credentials
        r = requests.post(
            "http://151.80.19.204/ints/signin",
            data={
                "username": "Nusrat005",
                "password": "shuvomia890"
            },
            timeout=15,
            allow_redirects=True
        )
        
        print(f"   Status: {r.status_code}")
        
        # Get OTP data
        if r.status_code == 200 or r.status_code == 302:
            print("✅ Login response received, fetching OTP...")
            
            r2 = session.get("http://151.80.19.204/ints/agent/SMSCDRStats", timeout=15)
            print(f"   CDR Status: {r2.status_code}")
            
            if r2.status_code == 200:
                # Extract using pure regex
                numbers = re.findall(r'<td[^>]*>(\d{11,15})</td>', r2.text)
                otps = re.findall(r'<td[^>]*>#\s*(\d{4,6})', r2.text)
                
                records = []
                for num, otp in zip(numbers, otps):
                    records.append({
                        "number": num,
                        "code": otp
                    })
                    print(f"   ✅ Found: {num} -> {otp}")
                
                return records
        
        return []
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

@bot.message_handler(func=lambda message: message.text in ["📱 GET NUMBER", "🔍 OTP SEARCH", "⚙️ ADMIN"])
def handle_menu(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text

    if text == "📱 GET NUMBER":
        markup = InlineKeyboardMarkup(row_width=1)
        for service in available_numbers.keys():
            markup.add(InlineKeyboardButton(f"📱 {service}", callback_data=f"service_{service}"))
        bot.send_message(chat_id, "SELECT SERVICE", reply_markup=markup)

    elif text == "🔍 OTP SEARCH":
        data = user_active_numbers.get(user_id)
        if not data:
            bot.send_message(chat_id, "❌ No number")
            return
        
        records = login_and_get_otp()
        
        if not records:
            bot.send_message(chat_id, "❌ No OTP")
            return
        
        for rec in records:
            if rec['number'] == data['number']:
                bot.send_message(chat_id, f"✨ OTP: {rec['code']}")
                return
        
        bot.send_message(chat_id, "❌ Not found")

    elif text == "⚙️ ADMIN" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("UPLOAD", callback_data="admin_upload"))
        bot.send_message(chat_id, "ADMIN", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("service_"))
def handle_service(call):
    chat_id = call.message.chat.id
    service = call.data.replace("service_", "")
    
    markup = InlineKeyboardMarkup(row_width=1)
    for country in available_numbers[service].keys():
        count = len(available_numbers[service][country])
        markup.add(InlineKeyboardButton(f"🌍 {country} ({count})", 
                  callback_data=f"country_{service}_{country}"))
    
    bot.edit_message_text("SELECT COUNTRY", chat_id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def handle_country(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    parts = call.data.replace("country_", "").split("_", 1)
    service, country = parts[0], parts[1]
    
    nums = available_numbers[service][country]
    if not nums:
        bot.send_message(chat_id, "❌ No numbers")
        return
    
    number = nums.pop(0)
    user_active_numbers[user_id] = {"number": number}
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔍 SEARCH", callback_data="search_otp"))
    
    bot.send_message(chat_id, f"✅ {number}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "search_otp")
def search(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = user_active_numbers.get(user_id)
    
    if not data:
        return
    
    bot.send_message(chat_id, "🔍 Searching...")
    
    records = login_and_get_otp()
    
    for rec in records:
        if rec['number'] == data['number']:
            bot.send_message(chat_id, f"✨ OTP: {rec['code']}")
            return
    
    bot.send_message(chat_id, "❌ Not found")

@bot.callback_query_handler(func=lambda call: call.data == "admin_upload")
def admin_upload(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        return
    
    chat_id = call.message.chat.id
    user_states[user_id] = "admin_service"
    bot.send_message(chat_id, "SERVICE:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == "admin_service")
def get_service(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    service = message.text.strip()
    
    if service not in available_numbers:
        available_numbers[service] = {}
    
    user_states[user_id] = f"admin_country_{service}"
    bot.send_message(chat_id, "COUNTRY:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, "").startswith("admin_country_"))
def get_country(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    service = user_states[user_id].replace("admin_country_", "")
    country = message.text.strip()
    
    if country not in available_numbers[service]:
        available_numbers[service][country] = []
    
    user_states[user_id] = f"admin_numbers_{service}_{country}"
    bot.send_message(chat_id, "NUMBERS:")

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, "").startswith("admin_numbers_"))
def get_numbers(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    state_info = user_states[user_id].replace("admin_numbers_", "").split("_", 1)
    service, country = state_info[0], state_info[1]
    
    numbers = [n.strip() for n in message.text.split("\n") if n.strip()]
    available_numbers[service][country].extend(numbers)
    
    user_states[user_id] = None
    bot.send_message(chat_id, f"✅ {len(numbers)} added!")

if __name__ == "__main__":
    print("✅ Ultra Simple Bot!")
    bot.infinity_polling()


