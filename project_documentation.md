# 📘 Sketch2Code: Complete System Documentation

Welcome to the comprehensive guide for **Sketch2Code**. This document provides an in-depth look at the architecture, modules, and workflows that enable hand-drawn sketches to be converted into functional code.

---

## 1. 🏗️ System Architecture Overview

Sketch2Code follows a **Micro-Service-inspired Monolithic Architecture** with a clear separation of concerns between the Web Server, AI Pipeline, and Data Management layer.

### Conversion Pipeline: How It Works

1. **Input Stage:** The user uploads a hand-drawn sketch (PNG/JPG).
2. **Preprocessing (OpenCV):**
   - Grayscale conversion and Gaussian Blurring.
   - Canny Edge Detection and Contour extraction.
   - Identifying Regions Of Interest (ROIs).
3. **Advanced Detection (Fast R-CNN / Seq2Seq):**
   - Custom PyTorch-based detection for complex UI layouts.
   - Attention-based Seq2Seq models for generating structured mappings.
4. **OCR & Keyword Mapping (PyTesseract):**
   - High-precision OCR on detected ROIs.
   - Classification using `MEANINGFUL_LABELS` (e.g., "Enter Email", "Login Button").
5. **Generative Mapping (Google Gemini API):**
   - Metadata (coordinates, text, labels) is sent to Gemini as a fallback/enhancement.
   - Context-aware generation of semantic HTML and CSS.
6. **Code Assembly:** Final code is stitched together and saved to the database.

---

## 2. 🔌 Backend Modules (Python/Flask)

The backend is built using **Flask 3.0.0** and modularized via Blueprints.

| File / Directory | Responsibility |
| :--- | :--- |
| `app.py` | Initializer: Configures Flask, secret keys, and registers blueprints. |
| `config.py` | Configuration management (MySQL, Gemini API, Upload folders). |
| `routes/auth.py` | Handles User Registration, Login (using password hashing), and Session management. |
| `routes/main.py` | The main engine: Orchestrates project creation, sketch uploads, and conversion trigger. |
| `routes/admin.py` | Admin-only interface for dataset management and model performance monitoring. |
| `inference.py` | **The Brain:** Coordinates OpenCV, PyTesseract, and ML models for the end-to-end conversion. |
| `database/db.py` | DBAL (Database Abstraction Layer) for safe MySQL/SQLite operations. |

### Key Code Snippet: The Detection Logic (inference.py)
The pipeline uses a hybrid method ensuring high reliability even with poor-quality sketches:
```python
def generate_code_from_sketch(image_path: str):
    # 1. OpenCV-based ROI Detection
    rois = detect_shapes(image_path)
    
    # 2. Text Extraction via OCR
    kw_data = ocr_service.associate_text_with_elements(image_path, rois)
    
    # 3. Model-based Refinement
    # (Optional) Refine layout using PyTorch-trained weights
    
    # 4. Multi-Format Code Generation
    html, css = build_html(kw_data)
    java = build_java(kw_data)
    
    return html, css, java
```

---

## 3. 🎨 Frontend Implementation

The frontend is a modern SPA-like (Single Page Application) experience within a Jinja2 multi-page setup.

- **Framework:** Bootstrap 5.3.
- **Interactivity:**
  - **AOS (Animate On Scroll):** Provides smooth entry animations for dashboard components.
  - **Prism.js:** Integrated into the "IDE Preview" for syntax highlighting of generated code.
  - **Live Preview:** An `<iframe>`-based viewer that renders generated HTML/CSS in real-time.
- **Theme Support:** Native Light/Dark mode implementation with persistent state (LocalStorage).

---

## 4. 🧠 Deep Learning Models (PyTorch)

Located in the `models/` directory, these provide the semantic intelligence for the system.

- **`detector.py`:** A convolutional neural network (CNN) designed to detect UI components (Buttons vs. Textboxes) regardless of drawing style.
- **`seq2seq.py`:** An Encoder-Decoder model with an **Attention Mechanism**.
  - **Encoder:** GRU-based, captures the spatial relationships between detected elements.
  - **Decoder:** Generates valid code sequences (DSL) that are later mapped to HTML.
- **`dataset.py`:** Custom PyTorch Dataset loader for training on the `dataset/` directory.

---

## 5. 🗄️ Database Schema

The system uses **MySQL** (Relational) with the following schema:

- **`users`:** Manages authentication and roles (`user` vs. `admin`).
- **`projects`:** Stores sketch metadata, binary image paths, and JSON/Text blobs for generated code.
- **`datasets`:** Tracks administrative uploads for retraining the AI models.

---

## 6. 🚀 Deployment & Production

The project is structured for high availability:
- **Procfile:** Configured for Heroku/Gunicorn.
- **Gunicorn:** Handles concurrent worker processes for CPU-intensive AI inference.
- **Environment Variables:** All secrets (DB passwords, API keys) are managed via `.env` to ensure security.

### Deploy Command:
```bash
gunicorn --workers 4 --timeout 120 --bind 0.0.0.0:$PORT app:app
```

---

*This documentation is automatically generated and updated as part of the Sketch2Code project lifecycle.*
