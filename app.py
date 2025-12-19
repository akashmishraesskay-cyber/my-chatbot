import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are the 'Esskay Beauty Expert'.
BUSINESS INFO: www.esskaybeauty.com
RULES:
1. GREETINGS: Say "Hello! Welcome to Esskay Beauty. ✨"
2. LINKS: Provide "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
3. GENERAL: Keep answers short.
"""

MODELS_TO_TRY = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash"]

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
                    
                    print(f"Received: {user_text}")

                    # --- DEBUGGING: PRINT VARIABLE NAMES ---
                    # This will show us if you made a typo (like 'GEMINI_KEY' or 'GEMINI_API_KEY ')
                    print("DEBUG: Current Environment Keys:", list(os.environ.keys()))
                    
                    bot_reply = smart_gemini_call(user_text)
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    # Double check if key exists
    if not GEMINI_API_KEY:
        return "⚠️ Error: GEMINI_API_KEY is missing. Check logs for available keys."

    # Combine Brain + User Message
    full_prompt = SYSTEM_PROMPT + "\n\nUser: " + text

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
        
        try:
            time.sleep(1)
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"Model {model_name} Error: {response.text}")
                continue
        except Exception as e:
            print(f"Connection Error: {e}")
            continue

    return "⚠️ System is busy. Please try again later."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("FB Token Missing")
        return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
