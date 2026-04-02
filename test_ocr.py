import pytesseract
import cv2
import os

# Try to find tesseract binary
possible_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Users\ELCOT\AppData\Local\Tesseract-OCR\tesseract.exe'
]

for path in possible_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break

try:
    img = cv2.imread(r'z:\s2c\static\uploads\m44log.jpg')
    text = pytesseract.image_to_string(img)
    print("OCR_SUCCESS")
    print(text)
except Exception as e:
    print(f"OCR_FAILED: {e}")
