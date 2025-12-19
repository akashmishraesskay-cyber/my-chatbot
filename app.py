import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

# List of models to try (in order of preference)
# We use your specific approved models from the list you sent earlier.
MODELS_TO_TRY = [
    "gemini-2.0-flash",       # Fast, standard
    "gemini-2.0-flash-lite",  # Super fast, often has separate quota
    "gemini-2.5-flash",       # Newer version
    "gemini-2.5-pro"          # More powerful backup
]

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
                    
                    print(f"Received from {sender_id}: {user_text}")

                    # Smart Call: Tries multiple models if one fails
                    bot_reply = smart_gemini_call(user_text)
                    
                    # Send reply to Facebook
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    """Tries multiple models until one works."""
    
    for model_name in MODELS_TO_TRY:
        print(f"Trying model: {model_name}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            # SUCCESS
            if response.status_code == 200:
                print(f"SUCCESS with {model_name}!")
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            
            # QUOTA ERROR (429) - Try next model
            elif response.status_code == 429:
                print(f"Model {model_name} is busy (429). Switching to next...")
                continue # Loop to the next model in the list
                
            # OTHER ERRORS (Like 404 or 500)
            else:
                print(f"Model {model_name} failed with {response.status_code}. Trying next...")
                continue

        except Exception as e:
            print(f"Connection failed on {model_name}: {e}")
            continue

    # If ALL models fail
    return "⚠️ All my brain cells are busy right now! Please wait 1 minute and try again."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("ERROR: FB_PAGE_ACCESS_TOKEN is missing!")
        return

    # Truncate to safety limit
    if len(text) > 1900:
        text = text[:1900] + "... (truncated)"

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print(f"FB ERROR: {r.text}")
    except Exception as e:
        print(f"FB EXCEPTION: {e}")

if __name__ == "__main__":
    app.run(port=5000)
