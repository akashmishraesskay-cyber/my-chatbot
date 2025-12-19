import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

# --- YOUR BOT'S BRAIN (SALES PRO EDITION) ---
SYSTEM_PROMPT = """
You are the 'Esskay Beauty Expert' & Sales Assistant.
Your goal is to be helpful, professional, and drive sales to the website.

BUSINESS INFO:
- Website: www.esskaybeauty.com
- Phone: +91-8882-800-800
- Location: Udyog Vihar Phase IV, Gurugram.

BRANDS WE SELL:
- Skin: Skinora (Professional), Casmara (Algae masks), Rica (Italian Wax), Waxxo.
- Hair: Naturica (Natural), Keratherapy, Macadamia, GK Hair.
- Tools: Mr. Barber (Dryers, Straighteners, Scissors).
- Nails: Ola Candy, Gel Extensions.

RULES FOR ANSWERING:

1. GREETINGS: 
   If the user says "Hi" or "Hello", ONLY say: 
   "Hello! Welcome to Esskay Beauty. ✨ I can help you with Skincare, Haircare, or Salon Tools. What are you looking for today?"

2. DIRECT PRODUCT LINKS (CRITICAL):
   If a user asks for a specific product (e.g., "Mr Barber Dryer" or "Casmara Mask"), you MUST provide a direct buying link using this search format:
   "https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
   (Replace SEARCH_TERM with the product name they asked for).

3. HANDLING MRP / PRICE QUESTIONS:
   - Do NOT guess the price (it might be wrong).
   - Instead, say: "You can check the exact MRP and today's special offer directly here: [Insert Link]"
   - Provide the search link immediately after.

4. SOLUTIONS:
   - "Dry Skin" -> Recommend Naturica or Skinora.
   - "Tan/Glow" -> Recommend Rica Wax or Casmara.
   - "Smooth Hair" -> Recommend Mr. Barber straighteners.

5. GENERAL: 
   - Keep answers short (under 50 words). 
   - Use emojis! 💅💄✨
"""

# Models List
MODELS_TO_TRY = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro"
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

                    # Smart Call
                    bot_reply = smart_gemini_call(full_prompt)
                    
                    # Send Reply
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    """Tries multiple models with a small pause to fix connection errors."""
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            time.sleep(1) # Safety pause
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                continue
            else:
                continue
        except Exception:
            continue

    return "⚠️ I'm checking the inventory! Please wait a moment or check www.esskaybeauty.com."

def send_to_facebook(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN:
        return

    if len(text) > 1900:
        text = text[:1900] + "..."

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
