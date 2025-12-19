import os
import requests
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
# Try to get token from Render environment
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
    
    # Simple log to show message arrived
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received from {sender_id}: {user_text}")

                    # Call Gemini
                    bot_reply = call_gemini_direct(user_text)
                    
                    # Send reply to Facebook
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def call_gemini_direct(text):
    """Talks to Gemini directly via URL."""
    # Using the model that we know exists for your key
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": text}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        # SUCCESS (200 OK)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        
        # RATE LIMIT / QUOTA ERROR (429)
        elif response.status_code == 429:
            print("GOOGLE QUOTA HIT (429)")
            return "⏳ I'm thinking too hard! Please wait 2 minutes and try again."
            
        # OTHER GOOGLE ERRORS
        else:
            print(f"GOOGLE ERROR {response.status_code}: {response.text}")
            return "I'm having trouble connecting to my brain. Try again later."
            
    except Exception as e:
        print(f"CONNECTION EXCEPTION: {e}")
        return "System error. Please try again."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("ERROR: FB_PAGE_ACCESS_TOKEN is missing!")
        return

    # SAFETY: Facebook rejects messages longer than 2000 chars.
    # We cut it off at 1900 to be safe.
    if len(text) > 1900:
        text = text[:1900] + "... (message too long, truncated)"

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print(f"FACEBOOK SEND ERROR: {r.text}")
    except Exception as e:
        print(f"FACEBOOK CONNECTION ERROR: {e}")

if __name__ == "__main__":
    app.run(port=5000)
