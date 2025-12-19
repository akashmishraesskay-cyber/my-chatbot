import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# --- CLEAN KEY ---
raw_key = os.environ.get("GEMINI_API_KEY")
if raw_key:
    GEMINI_API_KEY = raw_key.strip()
else:
    GEMINI_API_KEY = None

# --- BRAIN (UPDATED LOGIC) ---
SYSTEM_PROMPT = """
You are the 'Esskay Beauty Expert'.
Your goal is to be helpful and drive sales, but behave like a human.

RULES FOR BEHAVIOR:
1. IF THE USER CHATS (e.g., "Hi", "How are you", "Good morning"):
   - Do NOT provide a link.
   - Just reply politely. (e.g., "I'm doing great! Ready to help you find the best salon products. ✨")

2. IF THE USER ASKS FOR A PRODUCT (e.g., "Price of dryer", "I need wax", "Shampoo"):
   - You MUST provide a search link using this EXACT format:
   - "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
   - (Replace SEARCH_TERM with the product keywords).
   - Example response: "We have great options! Check the latest prices here: [Link]"

3. GENERAL:
   - Keep answers short (under 50 words).
   - Use emojis! 💅🛍️
"""

# --- MODEL LIST (Prioritizing Stability) ---
# We use 1.5-flash first because it has the highest rate limits (less "High Traffic" errors)
MODELS_TO_TRY = [
    "gemini-1.5-flash", 
    "gemini-2.0-flash"
]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.json
    # Listen to both Facebook (page) and Instagram
    if data.get("object") == "page" or data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received: {user_text}")
                    
                    # AI Call
                    bot_reply = smart_gemini_call(SYSTEM_PROMPT + "\n\nUser: " + user_text)
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    if not GEMINI_API_KEY:
        return "⚠️ Error: API Key missing in Render."

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            # 2-second pause to prevent speed blocks (Crucial for fixing your issue)
            time.sleep(2) 
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                print(f"⚠️ Rate Limit on {model_name}. Switching...")
                continue # Try next model
            elif response.status_code == 403:
                return "❌ Key Error: Your API Key is invalid. Please generate a new one."
            else:
                print(f"⚠️ Error {response.status_code} on {model_name}")
                continue
                
        except Exception as e:
            print(f"Connection Error: {e}")
            continue

    # If all models are busy
    return "⚠️ High traffic! Please wait 1 minute before asking again."

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
