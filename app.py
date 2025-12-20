import os
import requests
import time
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURATION ---
META_VERIFY_TOKEN = "my_secret_bot_123"
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# --- AUTO-CLEAN KEY ---
raw_key = os.environ.get("GEMINI_API_KEY")
if raw_key:
    GEMINI_API_KEY = raw_key.strip()
else:
    GEMINI_API_KEY = None

# --- MASSIVE PRODUCT DATABASE (Editable) ---
# I have added the exact prices found on your website.
KNOWLEDGE_BASE = """
TOP SELLING PRODUCTS & EXACT PRICES:

--- MR. BARBER (Electronics) ---
1. Mr. Barber Autograph Pro Dryer: Offer ₹20,690 (MRP ₹22,990)
2. Mr. Barber Airmax Dryer (2400W): Offer ₹3,150 (MRP ₹4,500)
3. Mr. Barber Straits Xtreme Straightener: Offer ₹2,730 (MRP ₹3,900)
4. Mr. Barber Infinity Pro Dryer (2000W): Offer ₹6,993 (MRP ₹9,990)
5. Mr. Barber Ultra Straits Pro Straightener: Offer ₹4,060 (MRP ₹5,800)
6. Mr. Barber Curler (4-in-1 Tong): Offer ₹6,650 (MRP ₹9,500)

--- RICA (Waxing) ---
7. Rica White Chocolate Wax (800ml): Offer ₹1,249 (MRP ₹1,350)
8. Rica Brazilian Beads (Stripless): Offer ₹1,615 (MRP ₹1,900)
9. Rica Aloe Vera Wax (800ml): Offer ₹1,256 (MRP ₹1,350)
10. Rica Dark Chocolate Wax (800ml): Offer ₹1,256 (MRP ₹1,350)
11. Rica Roll-On Wax (Refill): Offer ₹295 (MRP ₹310)

--- CASMARA (Skincare) ---
12. Casmara Algae Peel-Off Mask (Green/Gold): ₹1,800 - ₹1,900
13. Casmara Urban Protect DD Cream (Sunscreen): ₹3,300
14. Casmara Photoaging Control Gel Cream SPF 50+: ₹3,200
15. Casmara Hydra Lifting Cream: ₹2,990
16. Casmara Balance Cleanser (150ml): ₹1,950

--- SKINORA (Skincare) ---
17. Skinora Sunscreen SPF 50: Offer ₹656 (MRP ₹690)
18. Skinora Detan Mask (500g): Offer ₹1,520 (MRP ₹1,600)
19. Skinora Vitamin C Serum: Offer ₹941 (MRP ₹990)
20. Skinora Hyaluronic Hydra Cream: Offer ₹751 (MRP ₹790)

--- WAXXO (Heaters) ---
21. Waxxo Single Wax Heater: Offer ₹1,920 (MRP ₹2,400)
22. Waxxo Double Wax Heater: Offer ₹5,440 (MRP ₹6,800)
23. Waxxo White Chocolate Wax (800ml): Offer ₹1,080 (MRP ₹1,350)

--- OTHER INFO ---
24. COURSES: Esskay Academy offers hair/beauty courses with job placement. Link: https://esskaygroup.org/esskay-academy/
25. CAREERS: Hiring for Sales/Education. Email: hr@esskaybeauty.com. Link: https://esskaygroup.org/careers/
"""

# --- BRAIN ---
SYSTEM_PROMPT = f"""
You are the 'Esskay Beauty Expert'.
{KNOWLEDGE_BASE}

RULES:
1. IGNORE ECHOES: If the message looks like a bot reply, ignore it.
2. CHATTING: If user says "Hi", "Hello", reply: "Hello! Welcome to Esskay Beauty. ✨ How can I help you today?"
3. EXACT PRODUCT: 
   - Check the list above first. If found, say: "The price for [Product] is [Price]. Buy here: https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
   - If NOT in the list, use the Smart Link: "Check the latest price here: https://esskaybeauty.com/catalogsearch/result/?q=SEARCH_TERM"
   - (Replace SEARCH_TERM with the specific product name, e.g. "Rica+Wax").
4. GENERAL: Keep it short. Use emojis 🛍️.
"""

# --- FAST MODEL LIST ---
MODELS_TO_TRY = [
    "gemini-2.0-flash-lite-preview-02-05", 
    "gemini-2.0-flash",
    "gemini-2.5-flash"
]

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == META_VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    data = request.json
    if data.get("object") == "page" or data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                
                # 🛑 IGNORE ECHOES 🛑
                if event.get("message", {}).get("is_echo"):
                    continue

                if "message" in event and "text" in event["message"]:
                    sender_id = event["sender"]["id"]
                    user_text = event["message"]["text"]
                    
                    print(f"Received: {user_text}")
                    
                    # Smart AI Call
                    bot_reply = smart_gemini_call(SYSTEM_PROMPT + "\n\nUser: " + user_text)
                    send_reply(sender_id, bot_reply)
    return "ok", 200

def smart_gemini_call(text):
    if not GEMINI_API_KEY: return "⚠️ Error: API Key missing."

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        
        try:
            # 8s timeout for speed
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                time.sleep(1) 
                continue
            else:
                continue
                
        except Exception:
            continue

    return "Please browse our full catalog here: https://esskaybeauty.com/"

def send_reply(recipient_id, text):
    if not FB_PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v21.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

if __name__ == "__main__":
    app.run(port=5000)
