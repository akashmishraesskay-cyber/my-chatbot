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

# --- PRODUCT DATA ---
PRODUCT_DATA = """
TOP SELLING PRODUCTS & PRICES:
1. Rica White Chocolate Wax (800ml): Offer ₹1,249
2. Casmara Algae Peel-Off Mask: ₹1,800 - ₹1,900
3. Mr. Barber Straits Xtreme Straightener: Offer ₹2,730
4. Mr. Barber Airmax Dryer: Offer ₹3,150
5. Waxxo Wax Heater: Offer ₹1,920
"""

# --- BRAIN ---
SYSTEM_PROMPT = f"""
You are the 'Esskay Beauty Expert'.
{PRODUCT_DATA}

RULES:
1. IF USER CHATS ("Hi", "How are you"): Reply politely. NO LINK.
2. IF USER ASKS PRODUCT ("Price of dryer", "wax"): 
   - You MUST provide a link: "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
3. GENERAL: Keep it short (max 2 sentences). Use emojis 🛍️.
"""

# --- MODEL LIST (Optimized for Free Tier) ---
# We use 'gemini-2.0-flash-lite' first because it allows MORE messages per minute.
MODELS_TO_TRY = [
    "gemini-2.0-flash-lite-preview-02-05", # Fastest / Cheapest
    "gemini-2.0-flash",                     # Standard Backup
    "gemini-2.5-flash"                      # Powerful Backup
]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.json
    if data.get("object") == "page" or data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received: {user_text}")
                    
                    # Smart Call with 'Patient Retry'
                    bot_reply = smart_gemini_call(SYSTEM_PROMPT + "\n\nUser: " + user_text)
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    if not GEMINI_API_KEY: return "⚠️ Error: API Key missing in Render."

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        # Try up to 3 times per model
        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
                
                elif response.status_code == 429:
                    # RATE LIMIT HIT! The bot will pause and retry.
                    wait_time = (attempt + 1) * 5  # Wait 5s, then 10s, then 15s
                    print(f"⚠️ High Traffic. Pausing for {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue 
                
                else:
                    # If it's a real error (not traffic), switch model
                    print(f"⚠️ {model_name} error {response.status_code}. Switching...")
                    break 
                    
            except Exception as e:
                print(f"Connection Error: {e}")
                time.sleep(2)
                continue

    return "⚠️ We are receiving very high traffic! Please try again in 1 minute."

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
