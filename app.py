import os
import requests
from flask import Flask, request

app = Flask(__name__)

# Load keys from Render
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return request.args.get("hub.challenge")

    # When you message the bot, it will reply with your VALID model list
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                if "message" in event:
                    sender_id = event["sender"]["id"]
                    
                    # SCAN FOR MODELS
                    reply = list_available_models()
                    send_to_facebook(sender_id, reply)
    return "ok", 200

def list_available_models():
    if not GEMINI_API_KEY:
        return "❌ Error: GEMINI_API_KEY missing in Render."

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Get list of names
            names = [m['name'] for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            # Format nicely for Facebook
            model_list = "\n".join(names[:10]) # Show top 10
            return f"✅ SUCCESS! Your Key supports these models:\n\n{model_list}\n\n(Tell me which one you see!)"
        else:
            return f"❌ Google Error: {response.status_code}\n{response.text[:200]}"
            
    except Exception as e:
        return f"Connection Failed: {e}"

def send_to_facebook(recipient_id, text):
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(port=5000)
