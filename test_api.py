import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_gemini_api():
    print("Testing Gemini API Key configuration...")
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set!")
        return False
        
    print(f"API Key found (starts with: {api_key[:5]}...)")
    
    # Simple test layout
    test_layout = {
        "elements": [
            {"type": "button", "x": 100, "y": 100, "width": 120, "height": 40}
        ]
    }
    
    prompt = f"Generate responsive HTML and CSS for the following UI elements layout. Only provide the raw HTML code (which should include the CSS inside a <style> tag) without any markdown formatting or explanation.\n\nLayout JSON:\n{json.dumps(test_layout, indent=2)}"
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts":[{"text": prompt}]}]
        }
        
        print("Sending test request to Gemini API...")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("SUCCESS! API Key is valid and working.")
            result = response.json()
            html_code = result['candidates'][0]['content']['parts'][0]['text']
            print(f"Received valid response: {len(html_code)} characters")
            return True
        else:
            print(f"API Error ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print(f"Exception during API call: {e}")
        return False

if __name__ == "__main__":
    test_gemini_api()
