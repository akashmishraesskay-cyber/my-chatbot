import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

# --- YOUR BOT'S BRAIN (TRAINING DATA) ---
SYSTEM_PROMPT = """
You are the helpful AI Sales Assistant for 'Esskay Beauty'. 
You help customers buy salon products, track orders, and find the best beauty items.

BUSINESS INFO:
- Website: www.esskaybeauty.com (Encourage them to visit!)
- Phone: +91-8882-800-800
- Email: onlinesales@esskaybeauty.com
- Location: Plot No. 31, Sector-18, Udyog Vihar Phase IV, Gurugram, India.

OUR TOP BRANDS & PRODUCTS:
- Hair: Keratherapy, Naturica, Mr. Barber (Tools like dryers/straighteners).
- Skin: Casmara (Facial kits, Algae masks), Rica (Waxing products).
- Nails: Ola Candy, Gel extensions.
- Salon Furniture: Chairs, beds, and trolleys.

RULES FOR ANSWERING:
1. If they ask for a price, say: "Please check the latest prices on our website here: https://esskaybeauty.com/"
2. If they ask "Where is my order?", ask for their Order ID or tell them to call +91-8882-800-800.
3. Be professional but friendly. Use emojis! ✨🛍️💅
4. If they ask for Salon Services (haircuts), explain we are a "Product Supplier" but they can visit our partners or academy.
5. Keep answers short (under 50 words).
"""

# Backup Models (in case one is busy)
MODELS_TO_TRY = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro"
]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    # 1. Verification
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    # 2. Handling Messages
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received from {sender_id}: {user_text}")

                    # Combine System Prompt + User Question
                    full_prompt = SYSTEM_PROMPT + "\n\nUser Question: " + user_text

                    # Smart Call
                    bot_reply = smart_gemini_call(full_prompt)
                    
                    # Send Reply
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    """Tries multiple models until one works."""
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                print(f"Model {model_name} busy, switching...")
                continue
            else:
                continue
        except Exception:
            continue

    return "⚠️ All our support lines are busy! Please check www.esskaybeauty.com or try again in a minute."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("Token missing")
        return

    if len(text) > 1900:
        text = text[:1900] + "..."

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
