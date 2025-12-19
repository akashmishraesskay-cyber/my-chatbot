import os
import requests
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION (Use Environment Variables for Security) ---
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
# Force the token to match what you typed in Facebook
META_VERIFY_TOKEN = "my_secret_bot_123"
GENAI_API_KEY = os.environ.get("GENAI_API_KEY")

# Setup Gemini
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    # 1. Verification for Meta (Done once during setup)
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    # 2. Handling Incoming Messages
    data = request.json
    if data.get("object") in ["page", "instagram"]:
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    user_text = messaging_event["message"]["text"]
                    
                    # Generate response from Gemini
                    response = model.generate_content(user_text)
                    
                    # Send response back via Meta Graph API
                    send_message(sender_id, response.text)
    return "ok", 200

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":

    app.run(port=5000)
