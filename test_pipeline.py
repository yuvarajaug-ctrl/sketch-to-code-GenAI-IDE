import os
import pytesseract
from dotenv import load_dotenv
load_dotenv()
from inference import detect_shapes, generate_code_from_sketch

def test_inference():
    print("Testing Element Detection Configuration...")
    
    # Check Tesseract explicitly
    print(f"Checking Tesseract...")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract version found: {version}")
    except Exception as e:
        print(f"Tesseract not found via pytesseract: {e}")
        from services.ocr_service import TESS_PATHS
        for p in TESS_PATHS:
            print(f"Checking path: {p} -> {'EXISTS' if os.path.exists(p) else 'MISSING'}")

    sample_image = os.path.join("dataset", "sketches", "button1.jpg")
    
    if not os.path.exists(sample_image):
        print(f"Test image not found at {sample_image}")
        return False
        
    try:
        elements = detect_shapes(sample_image)
        print(f"Success! Detected {len(elements)} elements.")
        for el in elements:
            print(f"  - {el['type']} at ({el['x']}, {el['y']}) [{el['width']}x{el['height']}]")
            
        print("\nTesting End-to-End Generate Sequence...")
        html, css, java = generate_code_from_sketch(sample_image)
        print(f"HTML String Length: {len(html)}")
        print(f"CSS String Length: {len(css)}")
        
        return True
    except Exception as e:
        print(f"Pipeline crashed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_inference()
