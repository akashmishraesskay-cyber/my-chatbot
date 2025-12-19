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

# --- AI CONFIG ---
SYSTEM_PROMPT = """
You are the Esskay Beauty Expert.
1. GREETINGS: "Hello! Welcome to Esskay Beauty. ✨ How can I help?"
2. PRICES: Give exact prices if known.
3. LINKS: Use https://esskaybeauty.com/catalogsearch/result/?q=PRODUCT
4. GENERAL: Keep it short.
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
                    
                    # 2. If AI fails, use SMART MANUAL FALLBACK
                    if not bot_reply:
                        bot_reply = smart_manual_reply(user_text)
                    
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def try_ai_reply(user_text):
    if not GEMINI_API_KEY: return None
    
    for model in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": SYSTEM_PROMPT + "\nUser: " + user_text}]}]}
        
        try:
            # 2-second timeout to check connection
            response = requests.post(url, headers=headers, json=payload, timeout=2)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            continue
    return None

def smart_manual_reply(text):
    """Answers specific questions when AI is dead."""
    text = text.lower()
    
    # 1. Company Info
    if "esskay" in text or "who are you" in text or "what is" in text:
        return "Esskay Beauty is India's leading supplier of professional salon products, including Rica, Casmara, and Mr. Barber. 💅"

    # 2. Location/Contact
    if "location" in text or "where" in text or "contact" in text:
        return "📍 We are located in Udyog Vihar Phase IV, Gurugram. Call us at +91-8882-800-800."

    # 3. Greetings
    if text in ["hi", "hello", "hey", "start"]:
        return "Hello! Welcome to Esskay Beauty. ✨ I can help you with Skincare, Haircare, or Salon Tools."

    # 4. Prices (Manual List)
    if "price" in text or "cost" in text:
        return "📋 **Best Sellers:**\n- Rica Wax: ₹1,249\n- Mr. Barber Dryer: ₹3,150\n- Casmara Mask: ₹1,800\n\nCheck more prices here: https://esskaybeauty.com/"

    # 5. Default Search Link (Only for product searches)
    clean_query = text.replace(" ", "+")
    return f"🔎 I found these results for you:\nhttps://esskaybeauty.com/catalogsearch/result/?q={clean_query}"

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
