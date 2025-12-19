import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# --- CLEAN KEY ---
raw_key = os.environ.get("GEMINI_API_KEY")
GEMINI_API_KEY = raw_key.strip() if raw_key else None

# --- MANUAL PRICES (For Backup) ---
PRICE_LIST = """
🔥 **Hot Deals:**
1. Rica Wax (800ml): ₹1,249
2. Mr. Barber Straightener: ₹2,730
3. Casmara Algae Mask: ₹1,800
4. Waxxo Heater: ₹1,920
"""

# --- AI PROMPT ---
SYSTEM_PROMPT = f"""
You are the Esskay Beauty Expert.
1. PRICES: Use this list:
{PRICE_LIST}
2. LINKS: Generate search links: https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM
3. GREETINGS: "Hello! Welcome to Esskay Beauty. ✨ How can I help?"
"""

MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-1.5-flash"]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.json
    if data.get("object") in ["page", "instagram"]:
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    # 1. Try AI First
                    bot_reply = try_ai_reply(user_text)
                    
                    # 2. If AI fails, use Smart Backup
                    if not bot_reply:
                        bot_reply = smart_backup_reply(user_text)
                    
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def try_ai_reply(user_text):
    if not GEMINI_API_KEY: return None
    
    for model in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": SYSTEM_PROMPT + "\nUser: " + user_text}]}]}
        
        try:
            # Quick 1s check
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            continue
            
    return None # Failed

def smart_backup_reply(text):
    """Generates a helpful reply even if AI is dead."""
    text_lower = text.lower()
    
    # 1. Greetings
    if text_lower in ["hi", "hello", "hey", "start"]:
        return "Hello! Welcome to Esskay Beauty. ✨ I can help you with Prices, Wax, or Salon Tools. What are you looking for?"
        
    # 2. Price Questions
    if "price" in text_lower or "cost" in text_lower:
        return f"📋 **Current Best Sellers:**\n{PRICE_LIST}\n\nFor other items, check here: https://esskaybeauty.com/"

    # 3. Smart Link Generator (The Magic Fix)
    # It takes WHATEVER the user typed and makes a link
    clean_query = text.replace(" ", "+")
    return f"🔎 Here are the results for '{text}':\nhttps://esskaybeauty.com/catalogsearch/result/?q={clean_query}\n\n(Click to see prices & buy! 🛍️)"

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
