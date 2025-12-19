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
if raw_key:
    GEMINI_API_KEY = raw_key.strip()
else:
    GEMINI_API_KEY = None

# --- BRAIN ---
SYSTEM_PROMPT = """
You are the 'Esskay Beauty Expert'.
1. GREETINGS: "Hello! Welcome to Esskay Beauty. ✨ How can I help?"
2. LINKS: Use this format: https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM
3. GENERAL: Keep it short.
"""

MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-1.5-flash"]

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
                    
                    # Call the diagnostic function
                    bot_reply = diagnostic_gemini_call(SYSTEM_PROMPT + "\n\nUser: " + user_text)
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def diagnostic_gemini_call(text):
    if not GEMINI_API_KEY:
        return "❌ SETUP ERROR: GEMINI_API_KEY is missing in Render."

    # Try the main model
    model_name = "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        elif response.status_code == 429:
            return f"⚠️ TOO FAST (Error 429): Google blocked us for spamming. Please wait 2 minutes."
        elif response.status_code == 403:
            return f"❌ KEY DEAD (Error 403): Your API Key is invalid or leaked. Create a new one."
        elif response.status_code == 404:
            return f"❌ MODEL ERROR (Error 404): This API key cannot access '{model_name}'."
        else:
            return f"⚠️ UNKNOWN ERROR: {response.status_code} - {response.text[:100]}"
            
    except Exception as e:
        return f"❌ CRASH: {str(e)}"

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
