import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

# --- SYSTEM PROMPT (BRAIN) ---
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

# --- NEW MODEL LIST (Using Experimental versions to bypass limits) ---
MODELS_TO_TRY = [
    "gemini-2.0-flash-exp",   # Often has fresh quota
    "gemini-2.0-flash",       # Standard
    "gemini-2.0-flash-lite",  # Lightweight
    "gemini-2.5-flash"        # Newer
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
    """Tries multiple models. If all fail, prints the specific error to logs."""
    
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            # Wait 2 seconds between tries to be polite to Google
            time.sleep(2) 
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                # LOG THE ERROR so we can see it in Render
                print(f"⚠️ Model {model_name} failed. Status: {response.status_code}. Error: {response.text}")
                continue
                
        except Exception as e:
            print(f"❌ Connection Error on {model_name}: {e}")
            continue

    # If we get here, ALL models failed.
    print("CRITICAL: All models failed. Sending fallback message.")
    return "⚠️ High traffic! Please wait 2 minutes before asking again, or check www.esskaybeauty.com."

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
