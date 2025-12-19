import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- DEBUG CONFIG ---
# We check what keys exist
print("--- DEBUG: LIST OF ENVIRONMENT KEYS ---")
for key in os.environ.keys():
    print(f"Key Found: '{key}'") # Quotes help spot spaces like 'Key '
print("---------------------------------------")

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
                if "message" in event:
                    sender_id = event["sender"]["id"]
                    if not FB_PAGE_ACCESS_TOKEN:
                        print("CRITICAL ERROR: Code tried to reply but FB_PAGE_ACCESS_TOKEN is None.")
                    else:
                        send_to_facebook(sender_id, "Test Reply - Token is working")
    return "ok", 200

def send_to_facebook(recipient_id, text):
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    r = requests.post(url, json=payload)
    print(f"FB Response: {r.text}")

if __name__ == "__main__":
    app.run(port=5000)
