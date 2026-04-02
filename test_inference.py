from inference import detect_elements
import os

sketch_path = r'z:\s2c\static\uploads\dummy_sketch.png'
if os.path.exists(sketch_path):
    print(f"Testing on {sketch_path}")
    elements = detect_elements(sketch_path)
    print(f"Found {len(elements)} elements.")
else:
    print(f"File not found: {sketch_path}")
