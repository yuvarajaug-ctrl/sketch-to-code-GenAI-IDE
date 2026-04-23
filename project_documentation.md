# 📘 Sketch2Code: Complete System Documentation

Welcome to the comprehensive guide for **Sketch2Code**. This document provides an in-depth look at the architecture, modules, and workflows that enable hand-drawn sketches to be converted into functional code for both Web and Desktop platforms.

---

## 1. 🏗️ System Architecture Overview

Sketch2Code follows a hybrid architecture combining modular web services with advanced AI inference.

### The Conversion & Editing Pipeline

1. **Detection (AI/CV):** Raw sketches are processed via OpenCV and PyTorch models to identify UI components.
2. **Standardization:** Detected elements are mapped to a high-level UI schema (JSON).
3. **Interactive Refinement (IDE):**
   - **Canvas Mode:** Users can visually refine the AI's output.
   - **Real-Time API:** Any change on the visual canvas triggers `/api/generate_code`, which uses Gemini and local engines to rebuild the source artifacts.
4. **Multi-Target Generation:**
   - **Web Target:** Semantic HTML5 and Bootstrap-driven CSS3.
   - **Desktop Target:** Native Java Swing source code.

---

## 2. 🖌️ The Interactive IDE (Frontend)

The Sketch2Code IDE is designed for maximum developer productivity.

### ✨ Visual Canvas Editor
The **Canvas Mode** transforms the detected elements into a list of interactive components.
- **Drag-and-Drop Reordering:** Using `Sortable.js`, users can physically rearrange the UI structure.
- **Dynamic Element Insertion:** Add new components like Radio Buttons, Dropdowns, or Images via a search-able toolbar.
- **Label Editing:** Change textbox labels or button text directly on the canvas with instant feedback.
- **Layout Presets:** Switch between "Login", "Signup", "Dashboard", and "Landing" modes to apply layout-specific generation rules.

### ⚡ Easy Live Preview
The IDE features a dual-view system:
- **IFrame Preview:** An isolated browser container that renders the code exactly as it would appear in production.
- **Twin Code Editors:** Integrated manual editors for HTML and CSS with auto-sync capabilities.

---

## 3. ☕ Cross-Platform Code Generation

Unlike standard tools, Sketch2Code generates valid source code for two distinct ecosystems:

### Web Platform (HTML/CSS)
- **Framework:** Responsive Bootstrap 5.
- **Design:** Modern typography (Inter) and custom glassmorphic styling.
- **Features:** Form validation hooks and interactive button states.

### Desktop Platform (Java Swing)
- **Language:** Pure Java.
- **Engine:** `services/keyword_engine.py` builds robust `JFrame`/`JPanel` hierarchies.
- **Architecture:** Generates a full `GeneratedUI.java` controller class that can be compiled and run as a standalone desktop application.

---

## 4. 🧠 Deep Learning & AI Modules

- **Custom Inference (`inference.py`):** Orchestrates the hand-off between OpenCV shape detection and GenAI mapping.
- **Gemini GenAI Integration:** Uses advanced prompts to translate visual hierarchies into clean, maintainable code.
- **Seq2Seq with Attention:** A recursive model used to predict the "next logical element" in a UI flow based on patterns in the training data.

---

## 5. 🗄️ Database & Deployment

- **MySQL Schema:** Robust handling of project versioning and user-specific datasets.
- **Production Ready:** Environment-aware config and Gunicorn support for high-concurrency AI processing.

---

*This document serves as the technical blueprint for the Sketch2Code ecosystem.*
