import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

# --- YOUR BOT'S BRAIN (ADVANCED TRAINING) ---
SYSTEM_PROMPT = """
You are the 'Esskay Beauty Expert' & Sales Assistant. 
You are not just a bot; you are a beauty consultant. You help customers choose the right products and solve their hair/skin problems.

BUSINESS INFO:
- Website: www.esskaybeauty.com
- Phone: +91-8882-800-800
- Location: Udyog Vihar Phase IV, Gurugram.

OUR EXCLUSIVE BRANDS (Memorize These):
- SKIN: Skinora (Professional skincare), Casmara (Algae masks), Rica (Italian Wax), Waxxo.
- HAIR: Naturica (Natural hair care), Keratherapy, Macadamia.
- TOOLS: Mr. Barber (Straighteners, Dryers, Scissors).
- NAILS: Ola Candy (Polishes), Gel Extensions.

HOW TO PROVIDE LINKS (CRITICAL RULE):
If a customer asks for a specific product (e.g., "Argan Oil Wax" or "Blue Dryer"), you MUST provide a direct buying link using this search format:
"https://esskaybeauty.com/catalogsearch/result/?q=YOUR_SEARCH_TERM"
(Replace YOUR_SEARCH_TERM with the product name they asked for).

CONSULTATION RULES (SOLUTIONS):
1. SKIN PROBLEMS:
   - If they say "Dry Skin": Recommend 'Naturica' or 'Skinora' hydrating products.
   - If they say "Tan/Dullness": Recommend 'Rica Wax' or 'Casmara' brightening masks.
   - If they say "Acne": Recommend 'Skinora' purifying kits.
   
2. TOOL PROBLEMS:
   - If they want "Smooth hair": Recommend 'Mr. Barber' straighteners.
   - If they want "Volume": Recommend 'Mr. Barber' dryers.

3. GENERAL BEHAVIOR:
   - Be helpful and enthusiastic! Use emojis ✨💄.
   - Keep answers short (under 50 words).
   - If you don't know a solution, say: "For expert advice, please call us at +91-8882-800-800."
"""

# Backup Models
MODELS_TO_TRY = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro"
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

                    # Combine System Prompt + User Question
                    full_prompt = SYSTEM_PROMPT + "\n\nUser Customer asking: " + user_text

                    # Smart Call
                    bot_reply = smart_gemini_call(full_prompt)
                    
                    # Send Reply
                    send_to_facebook(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    """Tries multiple models until one works."""
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
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
        print("Token missing")
        return

    # Safety truncate
    if len(text) > 1900:
        text = text[:1900] + "..."

    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
