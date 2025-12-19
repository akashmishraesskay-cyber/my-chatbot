import os
import requests
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
# 1. Verification Token for Facebook
META_VERIFY_TOKEN = "my_secret_bot_123"

# 2. Page Access Token (From Environment or Hardcoded)
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# 3. GOOGLE API KEY (HARDCODED FOR TESTING)
# Paste your key inside the quotes below
MY_GOOGLE_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

genai.configure(api_key=MY_GOOGLE_KEY)

# Using the most standard model to be safe
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    # Verification
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    # Handling Messages
    data = request.json
    print("Received Data:", data) # distinct log to prove new code is running

    if data.get("object") in ["page", "instagram"]:
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                # Ignore delivery confirmations, only want messages
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    sender_id = messaging_event["sender"]["id"]
                    user_text = messaging_event["message"]["text"]
                    
                    try:
                        # Try to get a response
                        response = model.generate_content(user_text)
                        bot_reply = response.text
                    except Exception as e:
                        bot_reply = f"Error from Google: {str(e)}"
                        print(f"GOOGLE ERROR: {e}")

                    # Send back to Facebook
                    send_message(sender_id, bot_reply)
    return "ok", 200

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    x = requests.post(url, json=payload)
    print("Sent to FB:", x.status_code, x.text)

if __name__ == "__main__":
    app.run(port=5000)
