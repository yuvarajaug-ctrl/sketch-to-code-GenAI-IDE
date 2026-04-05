# 🎨 Sketch2Code GenAI IDE

**Sketch2Code** is an advanced AI-powered platform that transforms hand-drawn UI sketches into production-ready front-end and back-end code. By combining Computer Vision, OCR, and Large Language Models, it automates the transition from design to development.

[![FastAPI](https://img.shields.io/badge/Backend-Flask-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/Database-MySQL-blue?style=for-the-badge&logo=mysql)](https://www.mysql.com/)
[![Gemini](https://img.shields.io/badge/AI-Google_Gemini-8E75B2?style=for-the-badge&logo=google-gemini)](https://deepmind.google/technologies/gemini/)
[![PyTorch](https://img.shields.io/badge/ML-PyTorch-EE4C2C?style=for-the-badge&logo=pytorch)](https://pytorch.org/)

---

## 🚀 Key Features

- **Intuitive Sketch Upload:** Simply upload a photo of your UI wireframe.
- **AI-Powered Detection:** Automatically detects UI components like Inputs, Buttons, Checkboxes, and Headings.
- **Multi-Code Generation:**
  - **Front-End:** Modern Responsive HTML5 & CSS3.
  - **Back-End:** Java Swing Controller logic.
- **Real-Time Preview:** Built-in IDE to view and test generated code instantly.
- **Admin Dashboard:** Manage datasets, monitor training, and optimize models.
- **Hybrid Pipeline:** Robust OCR-driven keyword detection combined with Gemini GenAI fallback for complex layouts.

---

## 🛠️ Tech Stack

### Frontend
- **Bootstrap 5 & AOS:** Modern, responsive design with smooth animations.
- **Prism.js:** Syntax highlighting for the generated code.
- **Custom IDE UI:** Integrated code editor and live preview panel.

### Backend
- **Flask (Python):** Scalable and flexible web framework.
- **MySQL:** Relational database for user and project management.
- **Gunicorn:** Production-ready WSGI server.

### AI/ML Pipeline
- **OpenCV:** Regional analysis and bounding box detection.
- **PyTesseract (OCR):** High-accuracy text extraction from sketches.
- **PyTorch:** Custom Faster R-CNN and Seq2Seq with Attention models.
- **Google Gemini API:** Generative AI for structural mapping and advanced code generation.

---

## 📖 Complete Documentation

For detailed information on the system architecture, module logic, and database schema, please refer to the:
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
   Create a `.env` file based on your credentials:
   ```env
   SECRET_KEY=your_secret_key
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DB=sketch2code_db
   GEMINI_API_KEY=your_gemini_api_key
   ```

4. **Initialize Database:**
   ```bash
   mysql -u root -p < database/schema.sql
   ```

5. **Run the Application:**
   ```bash
   python app.py
   ```
   Visit `http://localhost:8000/` in your browser.

---

## 📂 Project Structure

```text
├── app.py              # Main Entry Point
├── inference.py        # AI Pipeline Orchestrator
├── requirements.txt    # Project Dependencies
├── database/           # DB Schema & Connectivity
├── routes/             # Web Blueprints (Auth, Admin, Main)
├── services/           # Logic (OCR, AI Generator, Engines)
├── models/             # PyTorch Architectures
├── static/             # Styles, Scripts, and UI Assets
└── templates/          # HTML Templates
```

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.
