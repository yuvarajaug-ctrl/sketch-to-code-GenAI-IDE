import os
import re
import json
import requests

def generate_html_from_layout(layout_json):
    """
    Sends the layout JSON to Gemini API to generate HTML and CSS separately.
    Returns a tuple: (html_code, css_code)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("GEMINI_API_KEY not found. Falling back to local generation.")
        return generate_basic_html_locally(layout_json)
        
    prompt = (
        "Generate a clean, modern HTML form from the following detected UI keywords. "
        "Return ONLY a raw JSON object with two keys: 'html' and 'css'. "
        "The 'html' must be semantic, use a clean vertical form layout (no absolute positioning), and link to 'style.css'. "
        "The 'css' should produce a polished, card-style form with a white background, rounded corners, and a soft shadow. "
        "Input keywords should become labeled <input> fields. Button keywords should become <button> elements. "
        "Do not include markdown code fences or explanations — just the raw JSON.\n\n"
        f"Detected Layout: {json.dumps(layout_json, indent=2)}"
    )
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts":[{"text": prompt}]}]
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        raw_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # Clean up code blocks if any
        raw_text = re.sub(r'```(?:json)?\n?', '', raw_text).split('```')[0].strip()
        
        try:
            code_json = json.loads(raw_text)
            html_code = code_json.get('html', '')
            css_code = code_json.get('css', '')
            return html_code, css_code
        except:
            # If not JSON, try to split manually or fall back
            return raw_text, ""
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}. Falling back to local generation.")
        return generate_basic_html_locally(layout_json)

def generate_basic_html_locally(layout_json):
    """
    SEQUENTIAL RULE-BASED LAYOUT BUILDER.
    Returns (html_code, css_code)
    """
    import re
    elements = layout_json.get("elements", [])
    
    # Sort elements by Y coordinate to ensure top-to-bottom sequence
    elements = sorted(elements, key=lambda e: e.get('y', 0))
    
    css_code = """
    body { background-color: #f7f9fc; color: #333; padding: 50px 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .form-container { background: #ffffff; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1); max-width: 480px; margin: 0 auto; }
    .form-label { font-weight: 500; font-size: 0.9rem; color: #4b5563; margin-bottom: 0.5rem; display: block; }
    .form-control { width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px; margin-bottom: 1.25rem; }
    .form-control:focus { outline: none; border-color: #2563eb; ring: 2px rgba(37, 99, 235, 0.2); }
    .btn-primary { background-color: #2563eb; color: white; border: none; padding: 0.85rem; font-weight: 600; border-radius: 8px; transition: all 0.2s; width: 100%; cursor: pointer; }
    .btn-primary:hover { background-color: #1d4ed8; }
    .image-placeholder { background: #f3f4f6; border: 2px dashed #d1d5db; height: 180px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #9ca3af; margin-bottom: 1.5rem; }
    .checkbox-group { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
    """
    
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='utf-8'>",
        "  <meta name='viewport' content='width=device-width, initial-scale=1'>",
        "  <title>Clean Layout Output</title>",
        "  <link rel='stylesheet' href='style.css'>",
        "</head>",
        "<body>",
        "  <div class='form-container'>"
    ]
    
    for el in elements:
        t = el.get("type", "unknown")
        text = el.get("text", el.get("label", ""))
        
        if t == "button":
            html_parts.append(f"    <div class='mt-4'>")
            html_parts.append(f"      <button class='btn btn-primary'>{text if text else 'Submit'}</button>")
            html_parts.append(f"    </div>")
            
        elif t == "textbox":
            html_parts.append(f"    <div class='mb-3'>")
            label_text = text if text else "Field"
            html_parts.append(f"      <label class='form-label'>{label_text}</label>")
            
            input_type = "password" if str(label_text).lower() == "password" else "text"
            placeholder_val = label_text if label_text else "..."
            html_parts.append(f"      <input type='{input_type}' class='form-control' placeholder='Enter {placeholder_val}...'>")
            html_parts.append(f"    </div>")
            
        elif t == "checkbox":
            label_val = text if text else "Option"
            html_parts.append(f"    <div class='checkbox-group'>")
            html_parts.append(f"      <input type='checkbox' id='chk_{hash(label_val)}' class='form-check-input'>")
            html_parts.append(f"      <label for='chk_{hash(label_val)}' class='form-check-label'>{label_val}</label>")
            html_parts.append(f"    </div>")
            
        elif t == "image":
            html_parts.append(f"    <div class='image-placeholder'>Image Placeholder</div>")
            
        elif t == "label":
             html_parts.append(f"    <h4 class='mb-3 text-center'>{text}</h4>")
            
    html_parts.append("  </div>")
    html_parts.append("</body>")
    html_parts.append("</html>")
    
    return "\n".join(html_parts), css_code
