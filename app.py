import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

# --- SYSTEM PROMPT ---
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

2. DIRECT LINKS: If asked for a product, provide this link:
   "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"

3. MRP/PRICE: Do not guess prices. Say: "Check the exact MRP and offers here: [Link]"

4. SOLUTIONS:
   - "Dry Skin" -> Recommend Naturica or Skinora.
   - "Tan" -> Recommend Rica Wax or Casmara.
   - "Smooth Hair" -> Recommend Mr. Barber.

5. GENERAL: Keep answers short (under 50 words). Use emojis! 💅
"""

# --- OPTIMIZED MODEL LIST (Removed blocked models) ---
# We prioritize "Lite" and "2.5" which usually have open quotas
MODELS_TO_TRY = [
    "gemini-2.0-flash-lite-preview-02-05", # Try the specific lite preview first
    "gemini-2.5-flash",                     # Try the newest 2.5
    "gemini-2.0-flash",                     # Standard backup
    "gemini-2.0-flash-001"                  # Stable backup
]

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
                    
                    print(f"Received from {sender_id}: {user_text}")

                    # Combine Brain + User Message
                    full_prompt = SYSTEM_PROMPT + "\n\nUser Question: " + user_text

                    # Smart Call
                    bot_reply = smart_gemini_call(full_prompt)
                    
                    # Send Reply
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    """Tries multiple models. Logs errors if they fail."""
    
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            # Short pause to prevent rate limiting
            time.sleep(1) 
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                # Log the error but keep going to the next model
                print(f"⚠️ {model_name} failed ({response.status_code}). Trying next...")
                continue
                
        except Exception as e:
            print(f"❌ Connection Error on {model_name}: {e}")
            continue

    # Fallback message if ALL fail
    return "⚠️ We are receiving high traffic! Please check www.esskaybeauty.com for prices."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("Error: Token missing")
        return

    if len(text) > 1900:
        text = text[:1900] + "..."

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
