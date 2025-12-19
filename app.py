import os
import requests
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# YOUR API KEY
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

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
                    
                    # Call Gemini using DIRECT method
                    bot_reply = call_gemini_direct(user_text)
                    
                    # Send reply to Facebook
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def call_gemini_direct(text):
    """Talks to Gemini directly via URL."""
    # !!! FIX IS HERE: Switched to 'gemini-pro' which is compatible with your key !!!
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": text}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error from Google: {response.text} (Status: {response.status_code})"
    except Exception as e:
        return f"Connection Failed: {str(e)}"

def send_to_facebook(recipient_id, text):
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
