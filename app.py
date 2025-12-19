import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# --- AUTO-CLEAN KEY ---
raw_key = os.environ.get("GEMINI_API_KEY")
if raw_key:
    GEMINI_API_KEY = raw_key.strip()
else:
    GEMINI_API_KEY = None

# --- PRODUCT CATALOG ---
PRODUCT_DATA = """
TOP SELLING PRODUCTS (Prices from Website):
1. Rica White Chocolate Wax (800ml): Offer ₹1,249
2. Rica Brazilian Wax (Avocado): Offer ₹1,249
3. Casmara Algae Peel-Off Mask: ₹1,800 - ₹1,900
4. Mr. Barber Straits Xtreme Straightener: Offer ₹2,730
5. Mr. Barber Airmax Dryer: Offer ₹3,150
6. Waxxo Wax Heater (Single): Offer ₹1,920
"""

# --- BRAIN ---
SYSTEM_PROMPT = f"""
You are the 'Esskay Beauty Expert'.
Your goal: Drive sales by giving EXACT prices and buying links.

{PRODUCT_DATA}

RULES:
1. GREETINGS: "Hello! Welcome to Esskay Beauty. ✨ I can help with Skincare, Haircare, or Salon Tools. What do you need?"
2. PRICES: Check the list above. If not found, say: "Please check the latest price here: [Link]"
3. LINKS: Always provide a search link: "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
4. GENERAL: Keep it short (under 50 words). Use emojis 🛍️.
"""

# Using the most stable model first to avoid rate limits
MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-1.5-flash"]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    # 1. Verification
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    # 2. Handling Messages (Facebook + Instagram)
    data = request.json
    if data.get("object") == "page" or data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    # Smart Call
                    bot_reply = smart_gemini_call(SYSTEM_PROMPT + "\n\nUser: " + user_text)
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    if not GEMINI_API_KEY: return "⚠️ Error: API Key missing in Render."

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            # WAIT 2 SECONDS to prevent Error 429
            time.sleep(2) 
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                # If busy, wait 5 seconds and try next model
                time.sleep(5)
                continue
            else:
                continue
        except Exception:
            continue

    return "⚠️ High traffic! Please check www.esskaybeauty.com/prices."

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    # Works for both FB and Insta
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
