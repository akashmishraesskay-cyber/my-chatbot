import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# --- CLEAN KEY (Crucial for safety) ---
raw_key = os.environ.get("GEMINI_API_KEY")
if raw_key:
    GEMINI_API_KEY = raw_key.strip()
else:
    GEMINI_API_KEY = None

# --- PRODUCT DATA ---
PRODUCT_DATA = """
TOP SELLING PRODUCTS (Use these prices):
1. Rica White Chocolate Wax (800ml): MRP ₹1,350 -> Offer ₹1,249
2. Casmara Algae Peel-Off Mask: MRP ₹1,800 - ₹1,900
3. Mr. Barber Straits Xtreme: MRP ₹3,900 -> Offer ₹2,730
4. Mr. Barber Airmax Dryer: MRP ₹4,500 -> Offer ₹3,150
5. Waxxo Wax Heater: MRP ₹2,400 -> Offer ₹1,920
"""

# --- BRAIN ---
SYSTEM_PROMPT = f"""
You are the 'Esskay Beauty Expert'.
Your goal: Drive sales but behave like a human.

{PRODUCT_DATA}

RULES:
1. IF USER CHATS (e.g., "Hi", "How are you"):
   - Reply politely. Do NOT provide a link.

2. IF USER ASKS FOR A PRODUCT (e.g., "Price of dryer", "I need wax"):
   - Check the list above for prices.
   - You MUST provide a search link: "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"

3. GENERAL: Keep it short (under 50 words). Use emojis 🛍️.
"""

# --- CORRECT MODEL LIST (Based on your Account) ---
# We ONLY use the models your account actually has access to.
MODELS_TO_TRY = [
    "gemini-2.5-flash",        # Your Best Model
    "gemini-2.0-flash",        # Your Backup
    "gemini-2.0-flash-lite"    # Your Fast Backup
]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.json
    # Listen to both Facebook (page) and Instagram
    if data.get("object") == "page" or data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received: {user_text}")
                    
                    # Generate Reply
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
            # 1-second pause to prevent speed blocks
            time.sleep(1) 
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 404:
                 # If 2.5 fails, it tries 2.0 automatically
                print(f"⚠️ {model_name} not found. Switching...")
                continue
            else:
                print(f"⚠️ Error {response.status_code} on {model_name}")
                continue
                
        except Exception as e:
            print(f"Connection Error: {e}")
            continue

    return "⚠️ High traffic! Please check www.esskaybeauty.com."

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
