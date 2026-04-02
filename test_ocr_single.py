import cv2
import os
from services.ocr_service import extract_text_from_roi

def test_multi_ocr():
    for name in ["button1.jpg", "button2.jpg", "textbox.jpeg"]:
        img_path = os.path.join("dataset", "sketches", name)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Image {name} not found")
            continue
            
        h, w = img.shape[:2]
        text = extract_text_from_roi(img, 0, 0, w, h)
        print(f"Detected text in {name}: '{text}'")

if __name__ == "__main__":
    test_multi_ocr()
