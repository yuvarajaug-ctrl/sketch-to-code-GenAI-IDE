# 🎨 Sketch2Code GenAI IDE

**Sketch2Code** is a revolutionary AI-powered platform that transforms hand-drawn UI sketches into production-ready front-end and back-end code. It features a high-fidelity Visual Canvas for real-time editing and multi-platform output generation.

[![FastAPI](https://img.shields.io/badge/Backend-Flask-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/Database-MySQL-blue?style=for-the-badge&logo=mysql)](https://www.mysql.com/)
[![Gemini](https://img.shields.io/badge/AI-Google_Gemini-8E75B2?style=for-the-badge&logo=google-gemini)](https://deepmind.google/technologies/gemini/)
[![PyTorch](https://img.shields.io/badge/ML-PyTorch-EE4C2C?style=for-the-badge&logo=pytorch)](https://pytorch.org/)

---

## 🚀 Key Features

### 🖌️ Visual Canvas & Interactive IDE
- **Visual UI Editor:** A powerful "Canvas Mode" allowing you to add, remove, and reorder elements (Buttons, Textboxes, Dropdowns, etc.) using simple drag-and-drop.
- **Easy Live Preview:** Experience instant code rendering. As you modify elements on the canvas, the system builds the corresponding code in real-time.
- **Integrated Code Editor:** Twin-panel editor for manual HTML and CSS fine-tuning with instant "Run Preview" capabilities.

### 🖥️ Cross-Platform Code Generation
- **Modern Web Output:** Produces semantic HTML5 and responsive CSS3 utilizing Bootstrap 5.
- **Desktop Application Logic:** Automatically generates **Java Swing (Pure Java)** code for building desktop GUI counterparts of your sketches.
- **Dynamic Formatting:** Choose between various page types like Login, Signup, Dashboard, and Landing layouts.

### 🧠 Intelligent Detection Pipeline
- **AI-Driven Recognition:** High-accuracy detection of UI components from raw sketches using custom Computer Vision models.
- **Contextual Generation:** Combines keyword-driven OCR with Google Gemini GenAI to understand the *intent* behind the sketch.

---

## 🛠️ Tech Stack

### Frontend & IDE
- **Bootstrap 5 & AOS:** Modern, premium design with smooth micro-animations.
- **Sortable.js:** Enables fluid drag-and-drop reordering on the visual canvas.
- **Prism.js:** Professional-grade syntax highlighting for all generated languages.

### Backend & AI
- **Flask (Python):** The backbone for API routing and project management.
- **AI Engine:**
  - **OpenCV:** Regional analysis and ROI detection.
  - **PyTesseract (OCR):** Fine-grained text extraction.
  - **PyTorch:** Custom Faster R-CNN and Seq2Seq architectures.
  - **Google Gemini API:** Generative AI for structural mapping and advanced code generation.

---

## 📖 Complete Documentation

For detailed information on the system architecture, module logic, and database schema:
- [**System Documentation (project_documentation.md)**](file:///z:/s2c/project_documentation.md)
- [**Deployment Guide (Procfile)**](file:///z:/s2c/Procfile)

---

## 💻 Local Setup

### Prerequisites
- Python 3.11+
- MySQL Server
- Tesseract OCR (installed on your system)

### Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yuvarajaug-ctrl/sketch-to-code.git
   cd sketch-to-code
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   MYSQL_PASSWORD=your_password
   # ... other settings in .env
   ```

4. **Run:**
   `python app.py` -> Visit `http://localhost:8000/`

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.
