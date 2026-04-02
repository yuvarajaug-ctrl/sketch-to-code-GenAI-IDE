import cv2
import pytesseract
import numpy as np
import os
import re

# Try to find tesseract executable in common Windows paths
TESS_PATHS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Users\ELCOT\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
    r'C:\Users\\' + os.getlogin() + r'\AppData\Local\Tesseract-OCR\tesseract.exe',
    r'/usr/bin/tesseract'
]

for path in TESS_PATHS:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break

MEANINGFUL_LABELS = [
    'email', 'password', 'login', 'sign in', 'submit', 'name', 
    'mobile', 'gender', 'first name', 'last name', 'username', 'register'
]

def clean_and_filter_text(text):
    """
    Stricstricted text filtering as per user requirements.
    Only allows meaningful UI words, ignores short strings and those with symbols/numbers.
    """
    if not text:
        return None
    
    # Remove non-alphanumeric and normalize
    # User requested: ignore results that contain numbers or random symbols
    # So we check if text is strictly alpha (excluding spaces for multi-word labels)
    clean_text = text.strip().lower()
    
    # Remove common OCR junk at start/end
    clean_text = re.sub(r'^[^a-z]+|[^a-z]+$', '', clean_text)
    
    if len(clean_text) < 3:
        return None
        
    # Strictly alpha-only (allowing spaces for 'sign in')
    if not re.match(r'^[a-z\s]+$', clean_text):
        return None
    
    # Check against meaningful labels (UI Dictionary)
    for label in MEANINGFUL_LABELS:
        if label in clean_text or clean_text in label:
            return label.title()
            
    return None

def preprocess_for_ocr(img):
    """
    Apply grayscale, thresholding and contrast enhancement
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
        
    # Standardize size for OCR if too small
    h, w = gray.shape
    if h < 30:
        scale = 30.0 / h
        gray = cv2.resize(gray, (int(w * scale), 30), interpolation=cv2.INTER_CUBIC)

    # Increase contrast
    gray = cv2.convertScaleAbs(gray, alpha=1.8, beta=0)
    
    # Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    return thresh

def extract_text_from_roi(image, x, y, w, h, psm=6):
    """
    Crop specific region and extract text using Tesseract
    """
    try:
        # Pad coordinates slightly
        padding = 8
        roi_x = max(0, x - padding)
        roi_y = max(0, y - padding)
        roi_w = min(image.shape[1] - roi_x, w + 2*padding)
        roi_h = min(image.shape[0] - roi_y, h + 2*padding)
        
        if roi_w <= 0 or roi_h <= 0: return None
        
        roi = image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        processed_roi = preprocess_for_ocr(roi)
        
        config = f'--psm {psm}'
        text = pytesseract.image_to_string(processed_roi, config=config).strip()
        
        return clean_and_filter_text(text)
    except Exception as e:
        # print(f"OCR failed for ROI: {e}")
        return None

def associate_text_with_elements(image_path, elements):
    """
    For each UI element, check for text inside it or directly above it.
    Prevents overlaps by removing labels that are associated with other components.
    """
    image = cv2.imread(image_path)
    if image is None:
        return elements
        
    # Sort elements by Y to process from top to bottom
    elements = sorted(elements, key=lambda e: e['y'])
    
    processed_elements = []
    labels_to_remove = set()
    
    # First pass: Associate text with containers (input, button, etc.)
    for i, el in enumerate(elements):
        if el['type'] == 'label':
            continue
            
        x, y, w, h = el['x'], el['y'], el['width'], el['height']
        
        # Check for text INSIDE
        text_inside = extract_text_from_roi(image, x, y, w, h, psm=6)
        
        # Check for text ABOVE
        above_h = 50
        above_y = max(0, y - above_h)
        # Scan slightly wider to catch labels
        text_above = extract_text_from_roi(image, x - 10, above_y, w + 20, above_h, psm=7)
        
        if el['type'] == 'button':
            el['text'] = text_inside if text_inside else "Button"
        elif el['type'] == 'textbox':
            if text_above:
                el['label'] = text_above
                # Look for existing 'label' type elements that match this text
                # to prevent duplicates
                for j, other in enumerate(elements):
                    if other['type'] == 'label':
                        ox, oy = other['x'], other['y']
                        # If label is close to our 'above' region
                        if abs(ox - x) < 50 and abs(oy - y) < 80:
                            labels_to_remove.add(j)
            else:
                el['label'] = "" # Let Gemini decide or leave blank
                
        elif el['type'] == 'checkbox':
            right_w = 200
            text_right = extract_text_from_roi(image, x + w, y - 5, right_w, h + 10, psm=7)
            if text_right:
                el['label'] = text_right
                for j, other in enumerate(elements):
                    if other['type'] == 'label':
                        ox, oy = other['x'], other['y']
                        if abs(ox - (x+w)) < 50 and abs(oy - y) < 40:
                            labels_to_remove.add(j)
    
    # Second pass: Keep remaining labels that weren't associated or removed
    for i, el in enumerate(elements):
        if i in labels_to_remove:
            continue
            
        if el['type'] == 'label':
            text = extract_text_from_roi(image, el['x'], el['y'], el['width'], el['height'], psm=7)
            if text:
                el['text'] = text
                processed_elements.append(el)
        else:
            processed_elements.append(el)
            
    # Final overlap check (one more safety layer)
    final_list = []
    for i, e1 in enumerate(processed_elements):
        keep = True
        for j, e2 in enumerate(final_list):
            # Check if e1 and e2 are too close / overlapping
            # Focus on labels overlapping with other things
            if e1['type'] == 'label' and e2['type'] != 'label':
                # Dist between centers
                c1x, c1y = e1['x'] + e1['width']/2, e1['y'] + e1['height']/2
                c2x, c2y = e2['x'] + e2['width']/2, e2['y'] + e2['height']/2
                if abs(c1x - c2x) < 30 and abs(c1y - c2y) < 30:
                    keep = False
                    break
        if keep:
            final_list.append(e1)
            
    return sorted(final_list, key=lambda e: e['y'])

