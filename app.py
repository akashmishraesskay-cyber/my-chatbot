import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# --- CRITICAL FIX: CLEAN THE KEY ---
raw_key = os.environ.get("GEMINI_API_KEY")
if raw_key:
    # This removes invisible spaces that cause Error 403
    GEMINI_API_KEY = raw_key.strip()
    print(f"✅ Key Loaded. Starts with: {GEMINI_API_KEY[:5]}... Ends with: ...{GEMINI_API_KEY[-5:]}")
else:
    GEMINI_API_KEY = None
    print("❌ CRITICAL ERROR: GEMINI_API_KEY is missing entirely.")

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are the 'Esskay Beauty Expert' & Sales Assistant.
BUSINESS INFO:
- Website: www.esskaybeauty.com
- Phone: +91-8882-800-800
RULES:
1. GREETINGS: Say "Hello! Welcome to Esskay Beauty. ✨ How can I help?"
2. LINKS: Provide "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
3. GENERAL: Keep answers short (under 50 words). Use emojis! 💅
"""

# Only use the models we confirmed your key supports
MODELS_TO_TRY = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash" 
]

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
                    
                    print(f"Received from {sender_id}: {user_text}")

                    # Combine Brain + User Message
                    full_prompt = SYSTEM_PROMPT + "\n\nUser Question: " + user_text

                    bot_reply = smart_gemini_call(full_prompt)
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    if not GEMINI_API_KEY:
        return "⚠️ Error: API Key is missing in Render Settings."

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            time.sleep(1) 
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                # Print the EXACT error from Google to the logs
                print(f"⚠️ {model_name} Error {response.status_code}: {response.text}")
                continue
                
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            continue

    return "⚠️ High traffic! Please check www.esskaybeauty.com."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        print("Error: FB Token Missing")
        return

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
