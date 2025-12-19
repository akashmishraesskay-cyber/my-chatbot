import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# --- AUTO-CLEAN KEY (Fixes Error 403) ---
raw_key = os.environ.get("GEMINI_API_KEY")
if raw_key:
    GEMINI_API_KEY = raw_key.strip()
else:
    GEMINI_API_KEY = None

# --- PRODUCT CATALOG (HARDCODED PRICES) ---
# I extracted these from your website just now.
# The bot will use these to answer specific price questions.
PRODUCT_DATA = """
TOP SELLING PRODUCTS & PRICES (Use these exactly):
1. Rica White Chocolate Wax (800ml): MRP ₹1,350 -> Offer Price ₹1,249
2. Rica Brazilian Wax (Avocado/Stripless): MRP ₹1,350 -> Offer Price ₹1,249
3. Casmara Algae Peel-Off Mask (Green/Gold): MRP ₹1,800 - ₹1,900
4. Mr. Barber Straits Xtreme Straightener: MRP ₹3,900 -> Offer Price ₹2,730
5. Mr. Barber Airmax Dryer (2200W): MRP ₹4,500 -> Offer Price ₹3,150
6. Naturica Repairing Deep Shampoo: MRP ₹1,900 -> Offer Price ₹1,606
7. Waxxo Wax Heater (Single): MRP ₹2,400 -> Offer Price ₹1,920
"""

# --- BRAIN ---
SYSTEM_PROMPT = f"""
You are the 'Esskay Beauty Expert'.
Your goal: Drive sales by giving EXACT prices and buying links.

{PRODUCT_DATA}

RULES:
1. GREETINGS: "Hello! Welcome to Esskay Beauty. ✨ I can help with Rica, Casmara, Mr. Barber, and more. What do you need?"

2. IF USER ASKS PRICE:
   - Check the "TOP SELLING PRODUCTS" list above.
   - If found, say: "The price for [Product] is currently [Price]. You can buy it here: [Generate Link]"
   - If NOT found, say: "Please check the latest price and offer here: [Generate Link]"

3. HOW TO GENERATE LINKS:
   - Always use: "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
   - Replace SEARCH_TERM with the product name (e.g., "Rica+Wax" or "Mr+Barber+Dryer").

4. GENERAL: Keep it short. Use emojis 🛍️.
"""

MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite"]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received: {user_text}")
                    bot_reply = smart_gemini_call(SYSTEM_PROMPT + "\n\nUser: " + user_text)
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    if not GEMINI_API_KEY: return "⚠️ Error: API Key missing in Render."

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            time.sleep(1)
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 403:
                print(f"⚠️ Key Blocked (403). Check Render Settings.")
                continue
            else:
                print(f"⚠️ {model_name} failed ({response.status_code}). Switching...")
                continue
        except Exception as e:
            print(f"Connection Error: {e}")
            continue

    return "⚠️ High traffic! Please check www.esskaybeauty.com."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
