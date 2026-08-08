import re
import os
import time
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get from environment or use default
TOKEN = os.getenv("BOT_TOKEN", "8738544813:AAG7WMbdgN7xXZwNGKrJrxCv6PBc_2c-0fA")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6136815573"))

bot = telebot.TeleBot(TOKEN)

user_states = {}
available_numbers = {"Facebook": {"Tanzania": []}}
user_active_numbers = {} 
sent_otps = set()

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    first_name = message.from_user.first_name or ""
    welcome_text = f"👋 Welcome {first_name}"
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("📱 GET NUMBER"),
        KeyboardButton("🔍 OTP SEARCH"),
    )
    
    if message.from_user.id == ADMIN_ID:
        markup.add(KeyboardButton("⚙️ ADMIN"))
        
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

def login_panel():
    """Panel Login"""
    try:
        print("\n🔐 Logging in...")
        response = session.get("http://151.80.19.204/ints/signin", timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            return False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Solve captcha
        print("📝 Solving captcha...")
        captcha_match = re.search(r'(\d+)\s*[\+\-\*]\s*(\d+)', soup.get_text())
        
        captcha_answer = "0"
        if captcha_match:
            try:
                captcha_answer = str(eval(captcha_match.group(0)))
                print(f"   Answer: {captcha_answer}")
            except:
                pass
        
        # Login
        print("📤 Submitting login...")
        payload = {
            "username": "Nusrat005",
            "password": "shuvomia890",
            "captcha": captcha_answer
        }
        
        response = session.post(
            "http://151.80.19.204/ints/signin",
            data=payload,
            timeout=15,
            allow_redirects=True
        )
        print(f"   Status: {response.status_code}")
        
        print("✅ Login done!")
        return True
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

def fetch_otp_data():
    """Fetch OTP from SMSCDRStats"""
    try:
        print("\n📊 Fetching OTP data...")
        
        response = session.get(
            "http://151.80.19.204/ints/agent/SMSCDRStats",
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Failed")
            return []
        
        print("🔍 Parsing...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        records = []
        
        # Find table
        table = soup.find('table')
        if table:
            print("✅ Table found!")
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 7:
                    try:
                        col3 = cells[2].get_text(strip=True)
                        col6 = cells[5].get_text(strip=True)
                        
                        num_match = re.search(r'(\d{11,15})', col3)
                        otp_match = re.search(r'#\s*(\d{4,6})', col6)
                        
                        if num_match and otp_match:
                            records.append({
                                "number": num_match.group(1),
                                "code": otp_match.group(1),
                                "sms": col6
                            })
                            print(f"  ✅ {num_match.group(1)} -> {otp_match.group(1)}")
                    except:
                        pass
        else:
            print("❌ Table not found, trying fallback...")
            pattern = r'(\d{11,15})[^#]*#\s*(\d{4,6})'
            for match in re.finditer(pattern, response.text):
                records.append({
                    "number": match.group(1),
                    "code": match.group(2),
                    "sms": response.text[match.start():match.end()][:80]
                })
        
        print(f"📊 Total: {len(records)} OTPs")
        return records
        
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
        check_otp(chat_id, user_id, data['number'])

    elif text == "⚙️ ADMIN" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("UPLOAD", callback_data="admin_upload"))
        bot.send_message(chat_id, "⚙️ ADMIN", reply_markup=markup)

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
    user_active_numbers[user_id] = {"number": number, "chat_id": chat_id}
    
    msg = f"✅ Number: `{number}`"
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔍 SEARCH", callback_data="search_otp"))
    
    bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "search_otp")
def search_otp_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = user_active_numbers.get(user_id)
    
    if not data:
        bot.send_message(chat_id, "No number")
        return
    
    check_otp(chat_id, user_id, data['number'])

def check_otp(chat_id, user_id, target_number):
    """Check OTP"""
    try:
        if not login_panel():
            bot.send_message(chat_id, "❌ Login failed")
            return
        
        records = fetch_otp_data()
        
        if not records:
            bot.send_message(chat_id, "❌ No OTP found")
            return
        
        for rec in records:
            if rec['number'] == target_number:
                msg = f"✨ OTP!\n\n📞 {rec['number']}\n🔑 {rec['code']}\n\n{rec['sms']}"
                bot.send_message(chat_id, msg)
                return
        
        bot.send_message(chat_id, f"❌ No OTP for {target_number}")
        
    except Exception as e:
        bot.send_message(chat_id, f"Error: {e}")

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
    print("✅ Bot Started on Render!")
    print(f"Token: {TOKEN[:20]}...")
    print(f"Admin: {ADMIN_ID}")
    bot.infinity_polling()


