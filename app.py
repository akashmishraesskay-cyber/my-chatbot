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

# --- PRODUCT DATA (Hardcoded for speed) ---
PRODUCT_DATA = """
TOP SELLING PRODUCTS (Offer Prices):
1. Rica White Chocolate Wax (800ml): ₹1,249
2. Casmara Algae Peel-Off Mask: ₹1,800 - ₹1,900
3. Mr. Barber Straits Xtreme Straightener: ₹2,730
4. Mr. Barber Airmax Dryer: ₹3,150
5. Waxxo Wax Heater: ₹1,920
"""

# --- BRAIN ---
SYSTEM_PROMPT = f"""
You are the 'Esskay Beauty Expert'.
{PRODUCT_DATA}

RULES:
1. IGNORE YOURSELF: If the input looks like a bot reply, do nothing.
2. CHATTING: If user says "Hi", "Hello", reply: "Hello! How can I help you with our salon products today? 🛍️"
3. EXACT PRODUCT: If user asks for a specific product (e.g. "Price of Autograph Pro"), reply with:
   "You can find the details and best price here: https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
   (Replace SEARCH_TERM with the product name).
4. VAGUE QUESTIONS: If user just says "Tell me the price" or "Price please" WITHOUT naming a product, ASK THEM: "Which product are you looking for?"
5. GENERAL: Keep it short.
"""

# --- FAST MODEL LIST ---
MODELS_TO_TRY = [
    "gemini-2.0-flash-lite-preview-02-05", 
    "gemini-2.0-flash",
    "gemini-2.5-flash"
]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.json
    # Handle Facebook Page & Instagram events
    if data.get("object") == "page" or data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                
                # --- CRITICAL FIX: IGNORE "ECHO" MESSAGES ---
                # This stops the bot from replying to itself
                if event.get("message", {}).get("is_echo"):
                    print("Ignoring Bot Echo")
                    continue

                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received from User: {user_text}")
                    
                    # Smart AI Call
                    bot_reply = smart_gemini_call(SYSTEM_PROMPT + "\n\nUser: " + user_text)
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    if not GEMINI_API_KEY: return "⚠️ Error: API Key missing."

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            # Short timeout to keep Facebook happy
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                print(f"⚠️ High Traffic on {model_name}. Switching...")
                continue
            else:
                print(f"⚠️ Error {response.status_code}. Switching...")
                continue
                
        except Exception as e:
            print(f"Connection Error: {e}")
            continue

    # Fallback if Google is totally dead
    return "I'm checking that! Please browse here: https://esskaybeauty.com/"

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

if __name__ == "__main__":
    app.run(port=5000)
