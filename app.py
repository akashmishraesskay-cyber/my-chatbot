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
You are the 'Esskay Beauty Expert'.
BUSINESS INFO:
- Website: www.esskaybeauty.com
- Phone: +91-8882-800-800
- Location: Udyog Vihar Phase IV, Gurugram.

RULES:
1. GREETINGS: Say "Hello! Welcome to Esskay Beauty. ✨ How can I help?"
2. LINKS: Provide "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
3. GENERAL: Keep answers short (under 50 words). Use emojis! 💅
"""

# --- DEBUG MODEL LIST ---
# We are trying the generic aliases which are often more stable
MODELS_TO_TRY = [
    "gemini-flash-latest",    # Points to the newest available flash
    "gemini-pro-latest",      # Points to the newest available pro
    "gemini-1.5-flash",       # Standard 1.5
    "gemini-2.0-flash"        # Standard 2.0
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
    """Tries models. Returns the ACTUAL ERROR if all fail."""
    last_error = ""
    
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            time.sleep(1) 
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                # Capture the error to show the user
                error_data = response.json().get('error', {})
                last_error = f"Model {model_name} Error: {error_data.get('message', response.text)}"
                print(f"⚠️ {last_error}")
                continue
                
        except Exception as e:
            last_error = str(e)
            continue

    # DEBUG MODE: The bot will tell you EXACTLY what is wrong
    return f"⚠️ SYSTEM ERROR: {last_error[:180]}... (Please check logs)"

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        return

    if len(text) > 1900:
        text = text[:1900] + "..."

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
