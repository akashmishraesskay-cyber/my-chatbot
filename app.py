import os
import requests
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
# We try to get the token from Render, but if it fails, we print an error
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# YOUR WORKING GOOGLE KEY
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
    print("INCOMING DATA:", data) # Log incoming message

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    # Call Gemini
                    print(f"Asking Gemini: {user_text}")
                    bot_reply = call_gemini_direct(user_text)
                    print(f"Gemini Reply: {bot_reply}")
                    
                    # Send reply to Facebook
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def call_gemini_direct(text):
    """Talks to Gemini directly via URL."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error from Google: {response.text}"
    except Exception as e:
        return f"Connection Failed: {str(e)}"

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("ERROR: FB_PAGE_ACCESS_TOKEN is missing in Render Environment!")
        return

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    
    # We now capture and print the result
    response = requests.post(url, json=payload)
    print(f"FACEBOOK SEND STATUS: {response.status_code}")
    print(f"FACEBOOK RESPONSE: {response.text}")

if __name__ == "__main__":
    app.run(port=5000)
