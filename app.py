import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
# Securely load keys from Render Environment
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- YOUR BOT'S BRAIN (SALES EXPERT) ---
SYSTEM_PROMPT = """
You are the 'Esskay Beauty Expert' & Sales Assistant.
Your goal is to be helpful, professional, and drive sales to the website.

BUSINESS INFO:
- Website: www.esskaybeauty.com
- Phone: +91-8882-800-800
- Location: Udyog Vihar Phase IV, Gurugram.

RULES FOR ANSWERING:
1. GREETINGS: If user says "Hi", "Hello", ONLY say: 
   "Hello! Welcome to Esskay Beauty. ✨ I can help you with Skincare, Haircare, or Salon Tools. What are you looking for today?"

2. DIRECT LINKS: If asked for a product (e.g., "Argan Wax", "Dryer"), you MUST provide this search link:
   "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
   (Replace SEARCH_TERM with the product name).

3. MRP/PRICE: Do not guess prices. Say: 
   "You can check the exact MRP and today's offers here: [Insert Search Link]"

4. SOLUTIONS:
   - "Dry Skin" -> Recommend Naturica or Skinora.
   - "Tan" -> Recommend Rica Wax or Casmara.
   - "Smooth Hair" -> Recommend Mr. Barber.

5. GENERAL: Keep answers short (under 50 words). Use emojis! 💅✨
"""

# --- FINAL MODEL LIST (Updated for your Key) ---
MODELS_TO_TRY = [
    "gemini-2.5-flash",        # Your BEST model (Newest)
    "gemini-2.0-flash",        # Standard fallback
    "gemini-2.0-flash-lite",   # Fast & lightweight
    "gemini-2.5-pro"           # Powerful fallback
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

                    # Combine Brain + User Message
                    full_prompt = SYSTEM_PROMPT + "\n\nUser Question: " + user_text

                    # Smart Call
                    bot_reply = smart_gemini_call(full_prompt)
                    
                    # Send Reply
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    """Tries the specific models your key supports."""
    
    if not GEMINI_API_KEY:
        return "⚠️ Setup Error: GEMINI_API_KEY is missing in Render Settings."

    for model_name in MODELS_TO_TRY:
        # Construct URL for the specific model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            # 1-second pause to match Google's speed limit safely
            time.sleep(1) 
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                # Print error to logs but try the next model silently
                print(f"⚠️ {model_name} failed ({response.status_code}). Switching...")
                continue
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            continue

    return "⚠️ We are receiving high traffic! Please check www.esskaybeauty.com for prices."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("Error: FB Token Missing in Render")
        return

    # Truncate to avoid Facebook limits
    if len(text) > 1900:
        text = text[:1900] + "..."

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
