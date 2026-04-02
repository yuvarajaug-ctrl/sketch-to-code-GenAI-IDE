import os
import requests

def list_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set")
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        models = response.json()
        for model in models.get('models', []):
            print(f"Name: {model['name']}, Methods: {model['supportedGenerationMethods']}")
    else:
        print(f"Error: {response.status_code}, {response.text}")

if __name__ == "__main__":
    list_models()
