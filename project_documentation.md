# Sketch2Code Project Documentation

Welcome to the documentation for the **Sketch2Code** project. This document outlines the overall architecture, core modules, and important code sections that make up the application.

## Overview
Sketch2Code is a Flask-based web application that converts hand-drawn UI sketches into working code. It uses a hybrid pipeline that combines Computer Vision (OpenCV) for bounding box detection, OCR (PyTesseract) for text extraction, and keyword-based generation logic to produce final UI code such as HTML/CSS, and Java Swing. Additionally, there are hooks for ML models (Faster R-CNN, Seq2Seq) and GenAI API fallbacks.

## Core File Structure
- `app.py`: The entry point for the Flask application.
- `config.py`: Application configurations (e.g., database, upload folders).
- `inference.py`: Orchestrates the inference pipeline.
- `routes/`: Flask blueprints for the web interface (`main.py`, `auth.py`, `admin.py`).
- `services/`: Core logic modules:
  - `keyword_engine.py`: OCR integration, keyword matching, and UI code generation.
  - `ai_generator.py`: Fallback for calling the Gemini API to generate HTML from coordinates.
- `models/`: PyTorch ML models.
  - `seq2seq.py`: Contains the Encoder-Decoder architecture with Attention.
  - `dataset.py` & `detector.py`: Datasets and bounding box detection logic.
- `train.py`: Training script for the ML models.
- `database/`: Database connectivity and schema definitions.

---

## Important Codes and Modules

### 1. Main Entry Point (`app.py`)
Sets up the Flask server, registers the blueprints (Routes), and ensures necessary directories exist before the server starts.
```python
import os
from flask import Flask
from config import Config
from routes.main import main_bp
from routes.auth import auth_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATASET_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRAINED_MODELS_FOLDER'], exist_ok=True)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
```

### 2. The Application Routes (`routes/main.py`)
Handles web requests such as rendering the dashboard and processing file uploads. For sketch processing, the uploaded file path is passed to the generation pipeline (`generate_code_from_sketch`).

```python
@main_bp.route('/detect/<int:project_id>')
def detect(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    # Fetch project and file details from DB ...
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], project['sketch_image_path'])
    
    # Run Inference
    html_code, css_code, java_code = generate_code_from_sketch(filepath)
    
    # Save Java code to a file as required
    java_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], "GeneratedController.java")
    with open(java_filepath, 'w') as f:
        f.write(java_code)
    
    # Update project with generated code in DB ...
    
    flash("AI Detection and Code Generation complete!", "success")
    return redirect(url_for('main.preview', project_id=project_id))
```

### 3. Inference Pipeline (`inference.py`)
Serves as the bridge between raw images, computer vision logic, and code generation. It uses OpenCV to detect shapes as a fallback, and a keyword-driven OCR engine for standard inputs.

```python
def generate_code_from_sketch(image_path: str) -> Tuple[str, str, str]:
    from services.keyword_engine import extract_ui_keywords, build_html_from_keywords, build_java_from_keywords

    # Step 1: OpenCV shape detection (secondary, feeds ROI OCR)
    opencv_shapes = detect_shapes(image_path)

    # Step 2: Keyword-driven OCR (primary)
    # Passing opencv_shapes lets the engine run targeted OCR on each block.
    kw_data = extract_ui_keywords(image_path, opencv_shapes=opencv_shapes)

    # Step 3: Build HTML/CSS from keywords 
    html_code, css_code = build_html_from_keywords(kw_data, opencv_hints=opencv_shapes)
    
    # Step 4: Build Java Swing code
    java_code = build_java_from_keywords(kw_data, opencv_hints=opencv_shapes)

    return html_code, css_code, java_code
```

### 4. Keyword Engine & OCR Code Generation (`services/keyword_engine.py`)
This file is the heavy lifter. It runs PyTesseract on multiple image pre-processing versions (upscaled, inverted, thresholded) to pull out keywords. It maps keywords to variables like "inputs", "headings", and "buttons" to programmatically assemble code.

#### Key Functions
- `_ocr_full_image` and `_ocr_roi`: Runs OCR using Tesseract over image variants and Region-of-Interest (ROIs) respectively.
- `extract_ui_keywords`: Finds and maps matches against `INPUT_KEYWORDS`, `BUTTON_KEYWORDS`, and `HEADING_KEYWORDS`.
- `build_html_from_keywords`: Uses the detected labels to stitch together semantic HTML outputs and a predefined Card CSS styling.

```python
def build_html_from_keywords(kw_data: Dict, opencv_hints: List = None) -> Tuple[str, str]:
    inputs   = kw_data.get('inputs',   [])
    buttons  = kw_data.get('buttons',  [])
    headings = kw_data.get('headings', [])

    # HTML building snippet
    html = ["<!DOCTYPE html>", "<html lang='en'>", ...]
    
    for field in inputs:
        fid = re.sub(r'\s+', '_', field.lower())
        itype = "password" if any(pv in field.lower() for pv in PASSWORD_VARIANTS) else "text"
        
        html.append(f"    <div class='form-group'>")
        html.append(f"      <label for='{fid}'>{field}</label>")
        html.append(f"      <input type='{itype}' id='{fid}' name='{fid}'>")
        html.append(f"    </div>")
    
    # Compile full HTML sequence
    return "\n".join(html), _CSS
```

### 5. Generative ML Module (`models/seq2seq.py`)
Contains the PyTorch logic to learn semantic mappings directly instead of solely relying on rule-based engines. Currently structured with a GRU-based sequence-to-sequence model utilizing Attention.

```python
class Seq2Seq(nn.Module):
    def __init__(self, encoder, decoder, device):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder
        self.device = device

    def forward(self, src, trg, teacher_forcing_ratio=0.5):
        batch_size = src.shape[1]
        trg_len = trg.shape[0]
        trg_vocab_size = self.decoder.output_dim
        
        outputs = torch.zeros(trg_len, batch_size, trg_vocab_size).to(self.device)
        encoder_outputs, hidden = self.encoder(src)
        input = trg[0,:]
        
        for t in range(1, trg_len):
            output, hidden = self.decoder(input, hidden, encoder_outputs)
            outputs[t] = output
            
            teacher_force = random.random() < teacher_forcing_ratio
            top1 = output.argmax(1) 
            input = trg[t] if teacher_force else top1
            
        return outputs
```

### 6. Training Script (`train.py`)
This script ties the detection system and the `seq2seq` models into a single training script `train_model()`, evaluating custom Datasets natively implemented in `models/dataset.py`.

```python
def train_model():
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    
    # Dataloaders
    dataset = SketchDataset(root_dir=dataset_dir, transforms=get_transform(train=True))
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    
    # Initialize Detector & Generator
    detector = get_detector_model(num_classes).to(device)
    generator = Seq2Seq(enc, dec, device).to(device)

    # Optimization
    optimizer_det = torch.optim.SGD(detector.parameters(), lr=0.005, momentum=0.9)
    optimizer_gen = optim.Adam(generator.parameters())

    for epoch in range(1, num_epochs + 1):
        train_detection(data_loader, detector, optimizer_det, device, epoch)
        train_generation(generator, optimizer_det, criterion_gen, device, epoch)
        
    # Save the trained models for inference
    torch.save(detector.state_dict(), detector_path)
    torch.save(generator.state_dict(), generator_path)
```
