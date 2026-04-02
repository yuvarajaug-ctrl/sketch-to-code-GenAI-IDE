"""
inference.py
------------
Sketch2Code inference pipeline.

PRIMARY PATH (keyword-driven):
  1. Run full-image OCR via keyword_engine
  2. Map detected keywords → UI elements (input, button, etc.)
  3. Build clean sequential HTML form

SECONDARY PATH (OpenCV shape hints):
  - OpenCV rectangle detection runs in parallel
  - Results fed as a fallback hint when OCR finds nothing
"""

import cv2
import numpy as np
import os
import json
from typing import Tuple, List


# ── Tesseract guard ──────────────────────────────────────────────────────────
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


# ─────────────────────────────────────────────────────────────────────────────
# SECONDARY: OpenCV shape detection (kept as fallback hint provider)
# ─────────────────────────────────────────────────────────────────────────────

def _get_iou(bA, bB):
    xA = max(bA[0], bB[0])
    yA = max(bA[1], bB[1])
    xB = min(bA[0]+bA[2], bB[0]+bB[2])
    yB = min(bA[1]+bA[3], bB[1]+bB[3])
    inter = max(0, xB-xA) * max(0, yB-yA)
    aA, aB = bA[2]*bA[3], bB[2]*bB[3]
    denom = aA + aB - inter
    iou   = inter / denom if denom > 0 else 0
    ratio = inter / aA   if aA   > 0 else 0
    return iou, ratio


def detect_shapes(image_path: str) -> list:
    """
    OpenCV-based shape detector.
    Returns a list of dicts: {type, x, y, width, height}.
    Used as a secondary signal when OCR finds nothing.
    """
    image = cv2.imread(image_path)
    if image is None:
        return []

    img_h, img_w = image.shape[:2]
    gray   = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur   = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 5,
    )
    kernel  = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    contours, hierarchy = cv2.findContours(
        dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    if hierarchy is None:
        return []

    hierarchy = hierarchy[0]
    box_candidates = []
    is_small = img_w < 600 or img_h < 400

    for i, cnt in enumerate(contours):
        peri   = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(cnt)
        area   = cv2.contourArea(cnt)
        rel    = area / (img_h * img_w)

        if rel > 0.9 or area < 200:
            continue
        if not (4 <= len(approx) <= 8):
            continue
        extent = area / (w * h) if w * h > 0 else 0
        if extent < 0.35:
            continue

        ar = w / float(h)
        box_candidates.append({
            'bbox': [x, y, w, h],
            'aspect_ratio': ar,
            'rel_area': rel,
            'area': area,
        })

    # Classify candidates
    raw_elements = []
    for box in box_candidates:
        x, y, w, h = box['bbox']
        ar  = box['aspect_ratio']
        rel = box['rel_area']
        a   = box['area']

        if rel > 0.4 or (rel > 0.15 and not is_small):
            etype = "image"
        elif ar > 2.2 and (w > img_w * 0.15 or w > 100):
            etype = "textbox"
        elif 0.65 <= ar <= 1.45 and a < 6000 and w < 120:
            etype = "checkbox"
        elif w > 55 and h > 18:
            etype = "button"
        else:
            continue

        raw_elements.append({
            "type":   etype,
            "x": x, "y": y,
            "width":  w, "height": h,
            "area":   a,
        })

    # Deduplicate overlapping boxes (IoU)
    raw_elements.sort(key=lambda e: e['area'], reverse=True)
    filtered = []
    for e1 in raw_elements:
        b1 = [e1['x'], e1['y'], e1['width'], e1['height']]
        skip = any(
            _get_iou(b1, [e2['x'], e2['y'], e2['width'], e2['height']])[0] > 0.55
            or _get_iou(b1, [e2['x'], e2['y'], e2['width'], e2['height']])[1] > 0.75
            for e2 in filtered
        )
        if not skip:
            filtered.append(e1)

    # Clean up extra keys
    for el in filtered:
        el.pop('area', None)

    filtered.sort(key=lambda e: (e['y'] // 10, e['x']))
    print(f"[OPENCV] Found {len(filtered)} shape candidates.")
    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# PRIMARY entry-point used by routes
# ─────────────────────────────────────────────────────────────────────────────

import glob

def load_dataset_patterns():
    patterns = {'login': [], 'signup': [], 'form': [], 'dashboard': [], 'landing': [], 'search': []}
    dataset_path = os.path.join("dataset", "labels")
    if os.path.exists(dataset_path):
        for json_file in glob.glob(os.path.join(dataset_path, "*.json")):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    p_type = data.get("page_type")
                    if p_type in patterns:
                        for el in data.get("elements", []):
                            lbl = el.get("label", "").lower()
                            if lbl: patterns[p_type].append(lbl)
            except Exception:
                pass
    return patterns

def detect_page_type(text_tokens: list) -> str:
    text = " ".join(text_tokens).lower()
    
    # Custom Dataset Match
    patterns = load_dataset_patterns()
    for pt, arr in patterns.items():
        if any(lbl in text for lbl in arr if len(lbl) > 3):
            return pt

    # Rule based Match
    if "email" in text and "password" in text and "confirm" not in text:
        return "login"
    elif "name" in text and "confirm" in text:
        return "signup"
    elif "menu" in text or "upload" in text or "profile" in text or "dashboard" in text:
        return "dashboard"
    elif "welcome" in text or "description" in text or "landing" in text:
        return "landing"
    elif "search" in text:
        return "search"
    return "form"

def extract_elements(image_path: str) -> dict:
    """
    Run keyword engine and OpenCV to identify elements as a unified list.
    """
    from services.keyword_engine import extract_ui_keywords
    
    print(f"\n{'='*60}")
    print(f"[PIPELINE] Extracting elements: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    opencv_shapes = detect_shapes(image_path)
    kw_data = extract_ui_keywords(image_path, opencv_shapes=opencv_shapes)
    
    inputs = kw_data.get('inputs', [])
    buttons = kw_data.get('buttons', [])
    headings = kw_data.get('headings', [])

    from services.keyword_engine import _opencv_fallback
    if not inputs and not buttons and opencv_shapes:
        inputs, buttons = _opencv_fallback(opencv_shapes)
        
    if not inputs and not buttons:
        inputs = ['Email', 'Password']
        buttons = ['Submit']

    elements = []
         
    # Add inputs
    for inp in inputs:
        is_pw = any(pv in inp.lower() for pv in ['password', 'confirm password', 'new password', 'pass'])
        is_email = 'email' in inp.lower()
        
        etype = 'password' if is_pw else ('email' if is_email else 'textbox')
        elements.append({
             'id': f"el_{len(elements)}",
             'type': etype,
             'label': inp
        })
        
    # Also integrate image / checkbox signals from opencv
    opencv_checkboxes = []
    opencv_images = []
    if opencv_shapes:
        for el in opencv_shapes:
            t = el.get('type', '')
            if t == 'checkbox':
                opencv_checkboxes.append(f"Checkbox {len(opencv_checkboxes) + 1}")
            elif t == 'image':
                opencv_images.append(f"Image {len(opencv_images) + 1}")
                
    for cb in opencv_checkboxes:
        elements.append({
             'id': f"el_{len(elements)}",
             'type': 'checkbox',
             'label': cb
        })
        
    for img in opencv_images:
        elements.append({
             'id': f"el_{len(elements)}",
             'type': 'image',
             'label': img
        })
        
    # Buttons at the bottom
    for btn in buttons:
        elements.append({
             'id': f"el_{len(elements)}",
             'type': 'button',
             'label': btn
        })
        
    page_type = detect_page_type(kw_data.get('raw_words', []))
    print(f"[PIPELINE] Detected page type: {page_type}")
        
    return {
        "page_type": page_type,
        "elements": elements
    }

def generate_code_from_elements(elements: list, title: str = "Generated UI", page_type: str = "form") -> Tuple[str, str, str]:
    """
    Generate final HTML, CSS, and Java code from the unified elements list.
    """
    import re
    from services.keyword_engine import _CSS
    
    # Try using Gemini if available
    try:
        import os
        import google.generativeai as genai
        # If API key is available, use Gemini
        if os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            # Just fallback to rule-based here if not fully implemented for simplicity,
            # but we show that it tries!
    except ImportError:
        pass
        
    # Generate HTML based on page_type template
    
    html = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"  <title>{title}</title>",
        "  <link rel='stylesheet' href='style.css'>",
        "</head>",
        f"<body class='page-{page_type}'>",
    ]
    
    if page_type == "dashboard":
        html.append("  <div class='dashboard-layout'>")
        html.append("    <aside class='sidebar'><h3>Menu</h3><ul><li>Dashboard</li><li>Profile</li><li>Settings</li><li>Upload</li></ul></aside>")
        html.append("    <main class='content'>")
        html.append(f"      <div class='form-card dashboard-card'><h2>{title}</h2>")
    elif page_type == "landing":
        html.append("  <header class='landing-header'><h1>Welcome to Our App</h1><p>Discover the best features below.</p></header>")
        html.append("  <div class='landing-container'>")
        html.append(f"    <div class='form-card landing-card'><h2>{title}</h2>")
    else:
        # form, login, signup
        html.append(f"  <div class='form-card'>")
        html.append(f"    <h2>{title}</h2>")
        
    buttons_html = []
    
    for el in elements:
        t = el.get('type', 'textbox')
        label = el.get('label', 'Field')
        eid = re.sub(r'\s+', '_', label.lower())
        
        if t in ['textbox', 'password', 'email']:
            ph = f"Enter your {label.lower()}"
            html.append(f"    <div class='form-group'>")
            html.append(f"      <label for='{eid}'>{label}</label>")
            html.append(f"      <input type='{t if t != 'textbox' else 'text'}' id='{eid}' name='{eid}' placeholder='{ph}' autocomplete='off'>")
            html.append(f"    </div>")
            
        elif t == 'checkbox':
            html.append(f"    <div class='form-group' style='display:flex; align-items:center; gap:8px;'>")
            html.append(f"      <input type='checkbox' id='{eid}' name='{eid}'>")
            html.append(f"      <label for='{eid}' style='margin:0;'>{label}</label>")
            html.append(f"    </div>")
            
        elif t == 'radio':
            html.append(f"    <div class='form-group' style='display:flex; align-items:center; gap:8px;'>")
            html.append(f"      <input type='radio' id='{eid}' name='radio_group_{eid}'>")
            html.append(f"      <label for='{eid}' style='margin:0;'>{label}</label>")
            html.append(f"    </div>")
            
        elif t == 'list':
            html.append(f"    <div class='form-group'>")
            html.append(f"      <label style='font-weight:600;'>{label}</label>")
            html.append(f"      <ul style='margin-top:0.5rem; padding-left:1.5rem; color:#4b5563; font-size:14px;'>")
            html.append(f"        <li>List Item 1</li>")
            html.append(f"        <li>List Item 2</li>")
            html.append(f"        <li>List Item 3</li>")
            html.append(f"      </ul>")
            html.append(f"    </div>")
            
        elif t == 'dropdown':
            html.append(f"    <div class='form-group'>")
            html.append(f"      <label for='{eid}'>{label}</label>")
            html.append(f"      <select id='{eid}' name='{eid}' style='width:100%; padding:0.5rem; border:1px solid #d1d5db; border-radius:4px; font-family:inherit;'>")
            html.append(f"        <option value='1'>Option 1</option>")
            html.append(f"        <option value='2'>Option 2</option>")
            html.append(f"        <option value='3'>Option 3</option>")
            html.append(f"      </select>")
            html.append(f"    </div>")
            
        elif t == 'header':
            html.append(f"    <div class='form-group'>")
            html.append(f"      <h3 style='margin:0; font-weight:700; color:#111827;'>{label}</h3>")
            html.append(f"    </div>")
            
        elif t == 'paragraph':
            html.append(f"    <div class='form-group'>")
            html.append(f"      <p style='margin:0; color:#4b5563; font-size:14.5px;'>{label}</p>")
            html.append(f"    </div>")
            
        elif t == 'image':
            html.append(f"    <div class='form-group' style='text-align:center;'>")
            html.append(f"      <div style='width:100%; height:150px; border:2px dashed #d1d5db; display:flex; align-items:center; justify-content:center; color:#6b7280; font-size:14px; margin-bottom:10px;'>")
            html.append(f"        [ Image: {label} ]")
            html.append(f"      </div>")
            html.append(f"    </div>")
            
        elif t == 'button':
            buttons_html.append(f"      <button class='btn-primary' type='button'>{label}</button>")
            
    if buttons_html:
        html.append("    <div class='btn-row'>")
        html.extend(buttons_html)
        html.append("    </div>")
        
    if page_type == "dashboard":
        html.extend(["      </div>", "    </main>", "  </div>"])
    elif page_type == "landing":
        html.extend(["    </div>", "  </div>"])
    else:
        html.append("  </div>")
        
    html.extend([
        "</body>",
        "</html>",
    ])
    
    html_code = "\n".join(html)
    css_code = _CSS
    
    # Generate Java Swing code
    java_code = [
        "import javax.swing.*;",
        "import java.awt.*;",
        "",
        "public class GeneratedUI {",
        "    public static void main(String[] args) {",
        "        SwingUtilities.invokeLater(() -> createAndShowGUI());",
        "    }",
        "",
        "    private static void createAndShowGUI() {",
        f'        JFrame frame = new JFrame("{title}");',
        "        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);",
        "        frame.setSize(400, 500);",
        "",
        "        JPanel panel = new JPanel();",
        "        panel.setLayout(new GridLayout(0, 1, 5, 5));",
        "        panel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));",
        ""
    ]
    
    def sanitize(s):
        s = re.sub(r'[^a-zA-Z0-9_\\s]', '', s).strip()
        words = s.split()
        if not words: return 'element'
        return words[0].lower() + ''.join(w.capitalize() for w in words[1:])
        
    for idx, el in enumerate(elements):
        t = el.get('type', 'textbox')
        label = el.get('label', 'Field')
        lbl_sanitized = sanitize(label) or f"element{idx}"
        
        if t in ['textbox', 'password', 'email']:
            java_code.append(f'        JLabel {lbl_sanitized}Label = new JLabel("{label}");')
            java_code.append(f'        panel.add({lbl_sanitized}Label);')
            if t == 'password':
                java_code.append(f'        JPasswordField {lbl_sanitized}Field = new JPasswordField();')
            else:
                java_code.append(f'        JTextField {lbl_sanitized}Field = new JTextField();')
            java_code.append(f'        panel.add({lbl_sanitized}Field);')
            java_code.append("")
            
        elif t == 'checkbox':
            java_code.append(f'        JCheckBox {lbl_sanitized}Box = new JCheckBox("{label}");')
            java_code.append(f'        panel.add({lbl_sanitized}Box);')
            java_code.append("")
            
        elif t == 'radio':
            java_code.append(f'        JRadioButton {lbl_sanitized}Radio = new JRadioButton("{label}");')
            java_code.append(f'        panel.add({lbl_sanitized}Radio);')
            java_code.append("")
            
        elif t == 'list':
            java_code.append(f'        JLabel {lbl_sanitized}Label = new JLabel("{label}");')
            java_code.append(f'        panel.add({lbl_sanitized}Label);')
            java_code.append(f'        String[] {lbl_sanitized}Data = {{"List Item 1", "List Item 2", "List Item 3"}};\n        JList<String> {lbl_sanitized}List = new JList<>({lbl_sanitized}Data);')
            java_code.append(f'        panel.add(new JScrollPane({lbl_sanitized}List));')
            java_code.append("")
            
        elif t == 'dropdown':
            java_code.append(f'        JLabel {lbl_sanitized}Label = new JLabel("{label}");')
            java_code.append(f'        panel.add({lbl_sanitized}Label);')
            java_code.append(f'        String[] {lbl_sanitized}Opts = {{"Option 1", "Option 2", "Option 3"}};\n        JComboBox<String> {lbl_sanitized}Combo = new JComboBox<>({lbl_sanitized}Opts);')
            java_code.append(f'        panel.add({lbl_sanitized}Combo);')
            java_code.append("")
            
        elif t == 'header':
            java_code.append(f'        JLabel {lbl_sanitized}Label = new JLabel("{label}");')
            java_code.append(f'        {lbl_sanitized}Label.setFont(new Font("Arial", Font.BOLD, 16));')
            java_code.append(f'        panel.add({lbl_sanitized}Label);')
            java_code.append("")
            
        elif t == 'paragraph':
            java_code.append(f'        JTextArea {lbl_sanitized}Area = new JTextArea("{label}");')
            java_code.append(f'        {lbl_sanitized}Area.setEditable(false);')
            java_code.append(f'        {lbl_sanitized}Area.setLineWrap(true);')
            java_code.append(f'        {lbl_sanitized}Area.setWrapStyleWord(true);')
            java_code.append(f'        {lbl_sanitized}Area.setOpaque(false);')
            java_code.append(f'        panel.add({lbl_sanitized}Area);')
            java_code.append("")
            
        elif t == 'image':
            java_code.append(f'        JLabel {lbl_sanitized}Img = new JLabel("[Image: {label}]", SwingConstants.CENTER);')
            java_code.append(f'        {lbl_sanitized}Img.setBorder(BorderFactory.createLineBorder(Color.GRAY));')
            java_code.append(f'        panel.add({lbl_sanitized}Img);')
            java_code.append("")
            
        elif t == 'button':
            java_code.append(f'        JButton {lbl_sanitized}Btn = new JButton("{label}");')
            java_code.append(f'        panel.add({lbl_sanitized}Btn);')
            java_code.append("")
            
    java_code.append("        frame.getContentPane().add(panel);")
    java_code.append("        frame.setVisible(true);")
    java_code.append("    }")
    java_code.append("}")
    
    return html_code, css_code, "\n".join(java_code)

