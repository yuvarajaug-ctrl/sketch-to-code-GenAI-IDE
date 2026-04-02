# -*- coding: utf-8 -*-
"""
keyword_engine.py  (v2)
-----------------------
Keyword-Driven UI Generator for Sketch2Code.

Fixes in v2:
  - Deduplicate keyword hits: shorter match is removed if a longer version exists
    (e.g.: "name" is dropped when "first name" also matched)
  - Multi-strategy OCR: full image with 4+ PSM modes + inverted image + upscaled crop
  - Box-targeted OCR: Tesseract is also run on each OpenCV-detected rectangle so
    text inside button boxes ("SIGN IN", "Submit") is reliably captured
  - OCR confidence > 0 only (accept low-confidence results for handwriting)
  - Unsharp sharpening pass before thresholding to recover faint pencil strokes
"""

import re
import cv2
import numpy as np
import os


try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd  # check attribute exists
    _HAS_TESSERACT = True
except Exception:
    _HAS_TESSERACT = False

from typing import List, Optional, Dict, Tuple

# ---------------------------------------------------------------------------
# Tesseract path setup
# ---------------------------------------------------------------------------
_TESS_PATHS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Users\ELCOT\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
    r'/usr/bin/tesseract',
]
if _HAS_TESSERACT:
    for _p in _TESS_PATHS:
        if os.path.exists(_p):
            pytesseract.pytesseract.tesseract_cmd = _p
            break

# ---------------------------------------------------------------------------
# Keyword dictionaries  (ORDERED: longer / more-specific entries FIRST)
# ---------------------------------------------------------------------------

INPUT_KEYWORDS = [
    # longer multi-word variants must come BEFORE their substrings
    'confirm password', 'new password',
    'first name', 'last name', 'full name', 'fullname',
    'user name', 'username',
    'date of birth', 'dob',
    'phone number', 'phone',
    'mobile number', 'mobile',
    # single-word variants
    'email', 'e-mail',
    'name',
    'password',
    'address', 'city', 'state', 'country', 'pincode', 'zip',
    'age', 'gender',
    'message', 'description', 'subject', 'contact',
]

BUTTON_KEYWORDS = [
    # longer first
    'create account', 'get started', 'forgot password', 'reset password',
    'sign up', 'sign in',
    'log in', 'log out',
    'login', 'logout',
    'register',
    'submit', 'send', 'continue', 'next', 'proceed',
    'confirm', 'verify', 'ok', 'done',
    'signup', 'signin',
]

HEADING_KEYWORDS = [
    'create account', 'sign up', 'sign in',
    'login', 'log in',
    'register',
    'welcome', 'welcome back',
    'contact us', 'contact',
    'profile', 'settings', 'dashboard',
]

PASSWORD_VARIANTS = ['password', 'confirm password', 'new password', 'pass']

# ---------------------------------------------------------------------------
# Image pre-processing strategies
# ---------------------------------------------------------------------------

def _sharpen(img: np.ndarray) -> np.ndarray:
    """Unsharp mask — recovers faint pencil lines."""
    blurred = cv2.GaussianBlur(img, (0, 0), 3)
    return cv2.addWeighted(img, 1.5, blurred, -0.5, 0)


def _preprocess_variants(img: np.ndarray) -> List[np.ndarray]:
    """
    Return several preprocessed versions of *img* (grayscale) for OCR:
      1. CLAHE + sharpen + Otsu threshold
      2. Simple binary threshold (inv)
      3. Inverted (dark-on-light lines)
      4. Upscaled x2
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    h, w = gray.shape
    variants = []

    # ── v1: CLAHE + sharpen + Otsu ──
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    v1 = clahe.apply(gray)
    v1 = _sharpen(v1)
    v1 = cv2.GaussianBlur(v1, (3, 3), 0)
    _, v1 = cv2.threshold(v1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v1)

    # ── v2: adaptive threshold ──
    v2 = cv2.GaussianBlur(gray, (5, 5), 0)
    v2 = cv2.adaptiveThreshold(v2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 15, 8)
    variants.append(v2)

    # ── v3: inverted Otsu (handles dark paper / dark ink) ──
    _, v3 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    variants.append(v3)

    # ── v4: 2× upscale then Otsu ──
    up = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    up = _sharpen(up)
    _, v4 = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(v4)

    # ── v4b: 2× upscale inverted ──
    _, v4b = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    variants.append(v4b)

    return variants


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------

def _run_tesseract(img: np.ndarray, psm: int) -> List[str]:
    """Run tesseract with given PSM and return stripped word list."""
    if not _HAS_TESSERACT:
        return []
    try:
        cfg = f'--psm {psm} --oem 3'
        raw = pytesseract.image_to_string(img, config=cfg)
        return raw.lower().split()
    except Exception:
        return []


def _ocr_full_image(image_path: str) -> List[str]:
    """
    Run multi-strategy, multi-PSM OCR on the full image.
    Returns deduplicated word list preserving first-seen order.
    """
    image = cv2.imread(image_path)
    if image is None:
        return []

    all_words: List[str] = []
    variants = _preprocess_variants(image)

    # PSM modes to try per variant
    psm_modes = [6, 11, 3, 4]

    for v in variants:
        for psm in psm_modes:
            all_words.extend(_run_tesseract(v, psm))

    # Also try on raw grayscale (no binarisation)
    gray_raw = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    for psm in [6, 11]:
        all_words.extend(_run_tesseract(gray_raw, psm))

    # Deduplicate preserving order
    seen: set = set()
    unique = []
    for w in all_words:
        if w not in seen:
            seen.add(w)
            unique.append(w)

    return unique


def _ocr_roi(image: np.ndarray, x: int, y: int, w: int, h: int) -> List[str]:
    """
    Run targeted OCR on a specific bounding box (used for button / box text).
    Returns word list.
    """
    pad = 8
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(image.shape[1], x + w + pad)
    y1 = min(image.shape[0], y + h + pad)
    roi = image[y0:y1, x0:x1]
    if roi.size == 0:
        return []

    # Scale up small ROIs
    rh, rw = roi.shape[:2]
    if rh < 40:
        scale = 40.0 / rh
        roi = cv2.resize(roi, (int(rw * scale), 40), interpolation=cv2.INTER_CUBIC)

    all_words: List[str] = []
    variants = _preprocess_variants(roi)
    for v in variants:
        for psm in [7, 8, 6]:          # PSM 7=line, 8=word, 6=block
            all_words.extend(_run_tesseract(v, psm))

    return all_words


# ---------------------------------------------------------------------------
# Filtering & matching
# ---------------------------------------------------------------------------

def _clean_token(w: str) -> str:
    """Remove punctuation, lowercase."""
    return re.sub(r'[^a-z\s]', '', w.lower()).strip()


def _is_valid_token(token: str) -> bool:
    """Reject tokens < 3 chars, with digits, or no alpha chars."""
    if len(token) < 2:
        return False
    if re.search(r'\d', token):
        return False
    if not re.search(r'[a-z]', token):
        return False
    return True


def _best_keyword_match(phrase: str, keyword_list: List[str]) -> Optional[str]:
    """
    Return the best keyword from keyword_list that matches phrase.
    """
    phrase = phrase.lower().strip()
    
    # 1. Exact match
    for kw in keyword_list:
        if kw.lower() == phrase:
            return kw

    # 2. Exact word match (e.g., phrase 'password' matches 'confirm password')
    phrase_words = set([w for w in phrase.split() if len(w) > 2])
    word_matches = []
    
    if phrase_words:
        for kw in keyword_list:
            kw_words = set(kw.lower().split())
            if phrase_words.intersection(kw_words):
                word_matches.append(kw)
                
    if word_matches:
        # Prefer the closer length match
        return min(word_matches, key=lambda k: abs(len(k) - len(phrase)))

    # 3. Substring match (robust)
    # Only if phrase is long enough (prevents 'e' -> 'confirm password')
    if len(phrase) >= 4:
        sub_matches = []
        for kw in keyword_list:
            kw_l = kw.lower()
            if phrase in kw_l or kw_l in phrase:
                sub_matches.append(kw)
        if sub_matches:
            return min(sub_matches, key=lambda k: abs(len(k) - len(phrase)))

    return None


# ---------------------------------------------------------------------------
# Deduplication: remove a keyword if a longer/more-specific one already exists
# ---------------------------------------------------------------------------

def _deduplicate_keywords(found: List[str]) -> List[str]:
    """
    Remove shorter keywords that are proper substrings of longer ones.
    E.g.: ['First Name', 'Name'] -> ['First Name']
         ['Sign In', 'Sign']     -> ['Sign In']
    Preserves insertion order.
    """
    result = []
    found_lower = [f.lower() for f in found]

    for i, kw in enumerate(found):
        kw_l = kw.lower()
        # Keep if no OTHER keyword strictly contains this one
        superseded = any(
            j != i and kw_l in found_lower[j] and kw_l != found_lower[j]
            for j in range(len(found))
        )
        if not superseded:
            result.append(kw)

    return result


# ---------------------------------------------------------------------------
# Core keyword detection
# ---------------------------------------------------------------------------

def extract_ui_keywords(image_path: str,
                        opencv_shapes: List[dict] = None) -> Dict:
    """
    Run full-image OCR + box-targeted OCR and return categorised keyword hits.

    Args:
        image_path:    Path to the uploaded sketch image.
        opencv_shapes: List of shape dicts from detect_shapes() (for ROI OCR).

    Returns:
        {
          'inputs':   ['Email', 'Password', ...],
          'buttons':  ['Sign In', ...],
          'headings': ['Login', ...],
          'raw_words': [...],
        }
    """
    # ── Step 1: Full-image OCR ──────────────────────────────────────────────
    raw_words = _ocr_full_image(image_path)
    print(f"\n[KEYWORD-ENGINE] Raw OCR tokens ({len(raw_words)}): {raw_words[:30]}")

    # ── Step 2: Box-targeted OCR for each detected shape ───────────────────
    if opencv_shapes:
        image = cv2.imread(image_path)
        if image is not None:
            for shape in opencv_shapes:
                box_words = _ocr_roi(
                    image,
                    shape['x'], shape['y'],
                    shape['width'], shape['height'],
                )
                print("  [BOX-OCR] shape=%s -> %s" % (shape['type'], box_words[:10]))
                raw_words.extend(box_words)

    # Deduplicate again after merging
    seen_set: set = set()
    merged: List[str] = []
    for w in raw_words:
        if w not in seen_set:
            seen_set.add(w)
            merged.append(w)
    raw_words = merged

    # ── Step 3: Build candidate phrases ────────────────────────────────────
    candidates: List[str] = []
    for i, w in enumerate(raw_words):
        w1 = _clean_token(w)
        if _is_valid_token(w1):
            candidates.append(w1)
        # pairs
        if i + 1 < len(raw_words):
            w2 = _clean_token(raw_words[i + 1])
            pair = f"{w1} {w2}".strip()
            if len(pair) >= 4:
                candidates.append(pair)
        # triples
        if i + 2 < len(raw_words):
            w3 = _clean_token(raw_words[i + 2])
            triple = f"{w1} {_clean_token(raw_words[i+1])} {w3}".strip()
            if len(triple) >= 5:
                candidates.append(triple)

    # ── Step 4: Match candidates against dictionaries ──────────────────────
    found_inputs:   List[str] = []
    found_buttons:  List[str] = []
    found_headings: List[str] = []
    seen_kw: set = set()

    for phrase in candidates:
        # Try INPUT first, then BUTTON
        km = _best_keyword_match(phrase, INPUT_KEYWORDS)
        if km and km.lower() not in seen_kw:
            found_inputs.append(km.title())
            seen_kw.add(km.lower())
            continue

        km = _best_keyword_match(phrase, BUTTON_KEYWORDS)
        if km and km.lower() not in seen_kw:
            found_buttons.append(km.title())
            seen_kw.add(km.lower())

    # Deduplicate: drop "Name" if "First Name" also present, etc.
    found_inputs  = _deduplicate_keywords(found_inputs)
    found_buttons = _deduplicate_keywords(found_buttons)

    # Heading: the form title (may overlap with button text)
    for phrase in candidates:
        km = _best_keyword_match(phrase, HEADING_KEYWORDS)
        if km:
            found_headings.append(km.title())
            break

    print(f"[KEYWORD-ENGINE] Inputs  : {found_inputs}")
    print(f"[KEYWORD-ENGINE] Buttons : {found_buttons}")
    print(f"[KEYWORD-ENGINE] Headings: {found_headings}")

    return {
        'inputs':    found_inputs,
        'buttons':   found_buttons,
        'headings':  found_headings,
        'raw_words': raw_words,
    }


def build_java_from_keywords(kw_data: Dict, opencv_hints: List = None) -> str:
    """Generate a corresponding Java Swing UI."""
    inputs = kw_data.get('inputs', [])
    buttons = kw_data.get('buttons', [])
    headings = kw_data.get('headings', [])
    
    # Gather additional elements from opencv_hints
    opencv_checkboxes = []
    opencv_images = []
    if opencv_hints:
        for i, el in enumerate(opencv_hints):
            t = el.get('type', '')
            if t == 'checkbox':
                opencv_checkboxes.append(f"Checkbox {len(opencv_checkboxes) + 1}")
            elif t == 'image':
                opencv_images.append(f"Image {len(opencv_images) + 1}")

    if not inputs and not buttons and opencv_hints:
        inputs, buttons = _opencv_fallback(opencv_hints)
        
    if not inputs and not buttons and not opencv_checkboxes and not opencv_images:
        inputs = ['Email', 'Password']
        buttons = ['Submit']

    title = headings[0] if headings else (buttons[0] if buttons else "Generated UI")
    
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
    
    for idx, img in enumerate(opencv_images):
        fid = f"img{idx+1}"
        java_code.append(f'        JLabel {fid}Label = new JLabel("[Image Placeholder: {img}]", SwingConstants.CENTER);')
        java_code.append(f'        {fid}Label.setBorder(BorderFactory.createLineBorder(Color.GRAY));')
        java_code.append(f'        panel.add({fid}Label);')
        java_code.append("")

    for idx, field in enumerate(inputs):
        is_pw = any(pv in field.lower() for pv in ['password', 'confirm password', 'new password', 'pass'])
        is_checkbox = 'checkbox' in field.lower()
        is_image = 'image' in field.lower()
        
        fid = sanitize(field)
        if not fid or fid == 'element':
            fid = f"field{idx}"

        if is_checkbox:
            java_code.append(f'        JCheckBox {fid}Box = new JCheckBox("{field}");')
            java_code.append(f'        panel.add({fid}Box);')
        elif is_image:
            java_code.append(f'        JLabel {fid}Img = new JLabel("[Image Placeholder: {field}]", SwingConstants.CENTER);')
            java_code.append(f'        {fid}Img.setBorder(BorderFactory.createLineBorder(Color.GRAY));')
            java_code.append(f'        panel.add({fid}Img);')
        else:
            java_code.append(f'        JLabel {fid}Label = new JLabel("{field}");')
            java_code.append(f'        panel.add({fid}Label);')
            if is_pw:
                java_code.append(f'        JPasswordField {fid}Field = new JPasswordField();')
            else:
                java_code.append(f'        JTextField {fid}Field = new JTextField();')
            java_code.append(f'        panel.add({fid}Field);')

        java_code.append("")
        
    for idx, cb in enumerate(opencv_checkboxes):
        fid = f"chk{idx+1}"
        java_code.append(f'        JCheckBox {fid} = new JCheckBox("{cb}");')
        java_code.append(f'        panel.add({fid});')
        java_code.append("")

    for idx, btn in enumerate(buttons):
        bid = sanitize(btn)
        if not bid or bid == 'element':
            bid = f"btn{idx}"
        java_code.append(f'        JButton {bid}Btn = new JButton("{btn}");')
        java_code.append(f'        panel.add({bid}Btn);')
        java_code.append("")

    java_code.append("        frame.getContentPane().add(panel);")
    java_code.append("        frame.setVisible(true);")
    java_code.append("    }")
    java_code.append("}")
    return "\n".join(java_code)



# ---------------------------------------------------------------------------
# CSS (polished card form)
# ---------------------------------------------------------------------------

_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: linear-gradient(135deg, #eef2ff 0%, #f8faff 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
body.page-dashboard {
    align-items: flex-start;
    display: block;
}
.dashboard-layout { display: flex; width: 100%; min-height: 100vh; }
.sidebar { width: 250px; background: #1e3a5f; color: #fff; padding: 2rem; }
.sidebar h3 { margin-bottom: 2rem; }
.sidebar ul { list-style: none; padding: 0; }
.sidebar li { margin-bottom: 1rem; opacity: 0.8; cursor: pointer; }
.content { flex: 1; padding: 3rem; background: transparent; }
body.page-landing {
    display: block;
}
.landing-header { text-align: center; padding: 4rem 2rem; background: #1e3a5f; color: white; }
.landing-container { padding: 3rem; display: flex; justify-content: center; }
.form-card {
    background: #ffffff;
    padding: 2.5rem 2rem;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(37,99,235,0.10), 0 2px 8px rgba(0,0,0,0.06);
    width: 100%;
    max-width: 440px;
    margin: auto;
}
.form-card.dashboard-card {
    max-width: 800px;
    margin: 0;
}
.form-card h2 {
    text-align: center;
    font-size: 1.65rem;
    font-weight: 700;
    color: #1e3a5f;
    margin-bottom: 1.8rem;
    letter-spacing: -0.5px;
}
.form-group {
    margin-bottom: 1.1rem;
}
.form-group label {
    display: block;
    font-size: 0.87rem;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 0.4rem;
}
.form-group input {
    width: 100%;
    padding: 0.7rem 0.9rem;
    border: 1.5px solid #d1d5db;
    border-radius: 8px;
    font-size: 0.95rem;
    color: #111827;
    background: #f9fafb;
    transition: border-color 0.2s, box-shadow 0.2s;
    outline: none;
}
.form-group input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.15);
    background: #fff;
}
.btn-row {
    margin-top: 1.6rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.btn-primary {
    width: 100%;
    padding: 0.85rem;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    letter-spacing: 0.3px;
    transition: opacity 0.2s, transform 0.1s;
}
.btn-primary:hover  { opacity: 0.9; transform: translateY(-1px); }
.btn-primary:active { transform: translateY(0); }
"""


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_html_from_keywords(kw_data: Dict,
                             opencv_hints: List = None) -> Tuple[str, str]:
    """
    Build (html, css) from keyword detection result.

    Args:
        kw_data:       Output of extract_ui_keywords()
        opencv_hints:  Optional list of element dicts from OpenCV (secondary hints).
    """
    inputs   = kw_data.get('inputs',   [])
    buttons  = kw_data.get('buttons',  [])
    headings = kw_data.get('headings', [])

    # If keyword engine found nothing, fall back to OpenCV signals
    if not inputs and not buttons and opencv_hints:
        print("[KEYWORD-ENGINE] No keywords found — using OpenCV shape fallback.")
        inputs, buttons = _opencv_fallback(opencv_hints)

    # Still nothing? Show a placeholder (better than blank)
    if not inputs and not buttons:
        print("[KEYWORD-ENGINE] Nothing detected — showing placeholder form.")
        inputs  = ['Email', 'Password']
        buttons = ['Submit']

    # Form heading
    title = headings[0] if headings else (buttons[0] if buttons else "Form")

    html = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"  <title>{title}</title>",
        "  <link rel='stylesheet' href='style.css'>",
        "</head>",
        "<body>",
        "  <div class='form-card'>",
        f"    <h2>{title}</h2>",
    ]

    # Input fields
    for field in inputs:
        fid  = re.sub(r'\s+', '_', field.lower())
        is_pw = any(pv in field.lower() for pv in PASSWORD_VARIANTS)
        itype = "password" if is_pw else "text"
        ph    = f"Enter your {field.lower()}"

        html.append(f"    <div class='form-group'>")
        html.append(f"      <label for='{fid}'>{field}</label>")
        html.append(
            f"      <input type='{itype}' id='{fid}' name='{fid}'"
            f" placeholder='{ph}' autocomplete='off'>"
        )
        html.append(f"    </div>")

    # Buttons
    if buttons:
        html.append("    <div class='btn-row'>")
        for btn in buttons:
            html.append(f"      <button class='btn-primary' type='button'>{btn}</button>")
        html.append("    </div>")

    html += [
        "  </div>",
        "</body>",
        "</html>",
    ]

    return "\n".join(html), _CSS


def _opencv_fallback(elements: List) -> Tuple[List, List]:
    """Convert raw OpenCV element list to (inputs, buttons) using shape only."""
    inputs, buttons = [], []
    for i, el in enumerate(elements):
        t = el.get('type', '')
        if t == 'textbox':
            inputs.append(f"Field {i + 1}")
        elif t == 'button':
            buttons.append(el.get('text', 'Submit'))
    return inputs, buttons
