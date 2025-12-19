import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
                    
                    # --- X-RAY DIAGNOSTIC ---
                    reply = test_google_connection()
                    send_to_facebook(sender_id, reply)
    return "ok", 200

def test_google_connection():
    if not GEMINI_API_KEY:
        return "❌ Error: GEMINI_API_KEY is missing from Render Settings."

    # Try a simple "Hello" to the most standard model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return "✅ SUCCESS! Google is connected perfectly. You can switch back to the main code."
        else:
            # THIS IS WHAT WE NEED TO SEE:
            return f"🔥 GOOGLE FAILED. Status: {response.status_code}\nReason: {response.text[:200]}"
            
    except Exception as e:
        return f"❌ Connection Crash: {str(e)}"

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
