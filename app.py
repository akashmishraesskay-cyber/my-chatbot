import os
import requests
from flask import Flask

app = Flask(__name__)

# YOUR API KEY
GEMINI_API_KEY = "AIzaSyA1MjIvEE5AMxpqnfRyFWZI6-RV0sW83sk"

@app.route("/", methods=['GET'])
def home():
    return "Bot is running! Go to /test to check your API key."

@app.route("/test", methods=['GET'])
def test_key():
    """Asks Google which models are available for this specific key."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json().get('models', [])
            # Create a clean list of allowed names
            names = [m['name'] for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            if not names:
                return "SUCCESS: Connected to Google, but NO models are available. (Your key might be restricted)."
            
            return f"SUCCESS! Your Valid Models: <br><br>" + "<br>".join(names)
        else:
            return f"ERROR: Google rejected the key. <br>Status: {response.status_code} <br>Message: {response.text}"
            
    except Exception as e:
        return f"CRITICAL ERROR: {str(e)}"

if __name__ == "__main__":
    app.run(port=5000)
