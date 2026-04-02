import os

files = {
    "requirements.txt": """Flask==3.0.0
PyMySQL==1.1.0
torch==2.1.0
torchvision==0.16.0
opencv-python==4.8.1.78
numpy==1.26.0
Flask-Session==0.5.0
Werkzeug==3.0.0
""",
    "app.py": """import os
from flask import Flask, session
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

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATASET_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRAINED_MODELS_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['DATASET_FOLDER'], 'sketches'), exist_ok=True)
os.makedirs(os.path.join(app.config['DATASET_FOLDER'], 'labels'), exist_ok=True)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
""",
    "config.py": """import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-sketch2code'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'sketch2code_db'
    
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
    DATASET_FOLDER = os.path.join(os.getcwd(), 'dataset')
    TRAINED_MODELS_FOLDER = os.path.join(os.getcwd(), 'trained_models')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB
""",
    "database/schema.sql": """CREATE DATABASE IF NOT EXISTS sketch2code_db;
USE sketch2code_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    sketch_image_path VARCHAR(255) NOT NULL,
    generated_html TEXT,
    generated_css TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS datasets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_path VARCHAR(255) NOT NULL,
    label_path VARCHAR(255) NOT NULL,
    uploaded_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);
""",
    "models/__init__.py": "",
    "routes/__init__.py": "",
    "routes/auth.py": """from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed. Check your setup.", "danger")
            return render_template('login.html')
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        if not conn:
            flash("Database connection failed", "danger")
            return render_template('register.html')
            
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)", 
                           (username, email, hashed_password, 'user'))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash('Email or Username already exists.', 'danger')
        finally:
            conn.close()
            
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
""",
    "database/db.py": """import mysql.connector
from config import Config
import logging

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        return connection
    except Exception as e:
        logging.error(f"Error connecting to MySQL: {e}")
        return None
""",
    "routes/main.py": """import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from inference import generate_code_from_sketch
from database.db import get_db_connection

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    conn = get_db_connection()
    projects = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
        projects = cursor.fetchall()
        conn.close()
        
    return render_template('dashboard.html', projects=projects)

@main_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        if 'sketch' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
            
        file = request.files['sketch']
        title = request.form.get('title', 'Untitled Project')
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Run Inference
            html_code, css_code = generate_code_from_sketch(filepath)
            
            # Save to DB
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO projects (user_id, title, sketch_image_path, generated_html, generated_css) VALUES (%s, %s, %s, %s, %s)",
                    (session['user_id'], title, filename, html_code, css_code)
                )
                conn.commit()
                project_id = cursor.lastrowid
                conn.close()
                return redirect(url_for('main.preview', project_id=project_id))
            else:
                flash('Database error while saving.', 'danger')
                
    return render_template('upload.html')

@main_bp.route('/preview/<int:project_id>')
def preview(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    conn = get_db_connection()
    if not conn:
        flash("DB connection error", "danger")
        return redirect(url_for('main.dashboard'))
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE id = %s AND user_id = %s", (project_id, session['user_id']))
    project = cursor.fetchone()
    conn.close()
    
    if not project:
        flash("Project not found", "danger")
        return redirect(url_for('main.dashboard'))
        
    return render_template('preview.html', project=project)
""",
    "routes/admin.py": """import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.utils import secure_filename
from database.db import get_db_connection
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def check_admin():
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('main.index'))

@admin_bp.route('/')
def dashboard():
    conn = get_db_connection()
    users_count = 0
    projects_count = 0
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as count FROM users")
        users_count = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM projects")
        projects_count = cursor.fetchone()['count']
        conn.close()
        
    return render_template('admin_dashboard.html', users_count=users_count, projects_count=projects_count)

@admin_bp.route('/dataset', methods=['GET', 'POST'])
def manage_dataset():
    if request.method == 'POST':
        image = request.files.get('image')
        labels = request.files.get('labels')
        
        if image and labels:
            image_name = secure_filename(image.filename)
            labels_name = secure_filename(labels.filename)
            
            image_path = os.path.join(current_app.config['DATASET_FOLDER'], 'sketches', image_name)
            label_path = os.path.join(current_app.config['DATASET_FOLDER'], 'labels', labels_name)
            
            image.save(image_path)
            labels.save(label_path)
            
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO datasets (image_path, label_path, uploaded_by) VALUES (%s, %s, %s)",
                              (image_name, labels_name, session['user_id']))
                conn.commit()
                conn.close()
            flash('Dataset item added successfully', 'success')
            return redirect(url_for('admin.manage_dataset'))
            
    conn = get_db_connection()
    datasets = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT d.*, u.username FROM datasets d JOIN users u ON d.uploaded_by = u.id ORDER BY d.created_at DESC")
        datasets = cursor.fetchall()
        conn.close()
        
    return render_template('admin_dataset.html', datasets=datasets)

@admin_bp.route('/train', methods=['POST'])
def train_model():
    # Mock behavior
    import subprocess
    train_script = os.path.join(os.getcwd(), 'train.py')
    subprocess.Popen(['python', train_script])
    flash("Model training started in the background", "info")
    return redirect(url_for('admin.dashboard'))
""",
    "inference.py": """import cv2
import numpy as np

def detect_elements(image_path):
    elements = [
        {"class": "label", "text": "Login Form", "bbox": [50, 20, 200, 50]},
        {"class": "textbox", "placeholder": "Username", "bbox": [50, 80, 400, 120]},
        {"class": "textbox", "placeholder": "Password", "bbox": [50, 140, 400, 180]},
        {"class": "button", "text": "Submit", "bbox": [50, 200, 150, 240]}
    ]
    return elements

def generate_code_from_sketch(image_path):
    elements = detect_elements(image_path)
    
    html_code = \"\"\"<div class="container mt-5">
    <div class="card shadow p-4 mx-auto" style="max-width: 500px;">
        <h3 class="mb-4 text-center">Login Form</h3>
        <form>
            <div class="mb-3">
                <input type="text" class="form-control" placeholder="Username">
            </div>
            <div class="mb-3">
                <input type="password" class="form-control" placeholder="Password">
            </div>
            <button class="btn btn-primary w-100">Submit</button>
        </form>
    </div>
</div>\"\"\"

    css_code = \"\"\"/* Auto-generated CSS */
body {
    background-color: #f8f9fa;
    font-family: 'Inter', sans-serif;
}
.card {
    border-radius: 12px;
    border: none;
}
\"\"\"
    return html_code, css_code
""",
    "train.py": """import time

def train_model():
    print("Starting Model Training for Sketch2Code GenAI IDE...")
    print("Loading dataset...")
    time.sleep(1)
    print("Initializing ResNet50 + FPN for Object Detection...")
    time.sleep(1)
    print("Initializing Seq2Seq Model with Attention...")
    
    epochs = 5
    for epoch in range(1, epochs + 1):
        print(f"Epoch {epoch}/{epochs}")
        time.sleep(0.5)
        print(f"  - Detection Loss: {0.5 / epoch:.4f} | Sequence Loss: {0.8 / epoch:.4f}")
        
    print("Training Complete. Models saved to trained_models/")
    
if __name__ == '__main__':
    train_model()
""",
    "templates/base.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sketch2Code GenAI IDE</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">
                <i class="fa-solid fa-wand-magic-sparkles text-primary"></i> Sketch2Code
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    {% if session.get('user_id') %}
                        {% if session.get('role') == 'admin' %}
                            <li class="nav-item">
                                <a class="nav-link" href="{{ url_for('admin.dashboard') }}">Admin Dashboard</a>
                            </li>
                        {% else %}
                            <li class="nav-item">
                                <a class="nav-link" href="{{ url_for('main.dashboard') }}">Dashboard</a>
                            </li>
                        {% endif %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('auth.logout') }}">Logout</a>
                        </li>
                    {% else %}
                        <li class="nav-item">
                            <a class="nav-link" href="{{ url_for('auth.login') }}">Login</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link btn btn-primary px-3 text-white" href="{{ url_for('auth.register') }}">Register</a>
                        </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
</body>
</html>
""",
    "templates/index.html": """{% extends 'base.html' %}
{% block content %}
<div class="row align-items-center mt-5">
    <div class="col-lg-6">
        <h1 class="display-4 fw-bold mb-4">Transform Sketches to <span class="text-primary">Working Code</span></h1>
        <p class="lead text-muted mb-4">Sketch2Code GenAI IDE uses advanced AI models (ResNet50 + Seq2Seq) to automatically convert hand-drawn UI wireframes into clean, structured HTML & CSS.</p>
        <div class="d-flex gap-3">
            <a href="{{ url_for('auth.register') }}" class="btn btn-primary btn-lg">Get Started</a>
            <a href="{{ url_for('auth.login') }}" class="btn btn-outline-secondary btn-lg">Login</a>
        </div>
    </div>
    <div class="col-lg-6 mt-5 mt-lg-0 text-center">
        <div class="card shadow-lg border-0 bg-dark text-white p-4">
            <i class="fa-solid fa-code display-1 text-primary mb-3"></i>
            <h3>AI Code Generation</h3>
            <p class="text-secondary">Upload a sketch, get production-ready HTML5 & Bootstrap 5 templates instantly.</p>
        </div>
    </div>
</div>
{% endblock %}
""",
    "templates/login.html": """{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center mt-5">
    <div class="col-md-5">
        <div class="card shadow-sm border-0">
            <div class="card-body p-4">
                <h3 class="text-center mb-4">Welcome Back</h3>
                <form method="POST" action="/login">
                    <div class="mb-3">
                        <label class="form-label">Email address</label>
                        <input type="email" name="email" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Login</button>
                </form>
                <div class="text-center mt-3">
                    <p>Don't have an account? <a href="/register">Register here</a>.</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    "templates/register.html": """{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center mt-5">
    <div class="col-md-5">
        <div class="card shadow-sm border-0">
            <div class="card-body p-4">
                <h3 class="text-center mb-4">Create an Account</h3>
                <form method="POST" action="/register">
                    <div class="mb-3">
                        <label class="form-label">Username</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email address</label>
                        <input type="email" name="email" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Register</button>
                </form>
                <div class="text-center mt-3">
                    <p>Already have an account? <a href="/login">Login here</a>.</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    "templates/dashboard.html": """{% extends 'base.html' %}
{% block content %}
<div class="row">
    <div class="col-md-3">
        <div class="list-group shadow-sm mb-4">
            <a href="/dashboard" class="list-group-item list-group-item-action active"><i class="fa-solid fa-home"></i> Dashboard</a>
            <a href="/upload" class="list-group-item list-group-item-action"><i class="fa-solid fa-upload"></i> Upload Sketch</a>
        </div>
    </div>
    <div class="col-md-9">
        <h2 class="mb-4">My Projects</h2>
        <div class="row">
            {% if projects %}
                {% for project in projects %}
                <div class="col-md-6 mb-4">
                    <div class="card shadow-sm h-100">
                        <img src="{{ url_for('static', filename='uploads/' + project.sketch_image_path) }}" class="card-img-top" style="height: 200px; object-fit: cover;">
                        <div class="card-body">
                            <h5 class="card-title">{{ project.title }}</h5>
                            <p class="text-muted small">Created: {{ project.created_at }}</p>
                            <a href="/preview/{{ project.id }}" class="btn btn-outline-primary btn-sm">View Result</a>
                        </div>
                    </div>
                </div>
                {% endendfor %}
            {% else %}
                <div class="col-12 text-center py-5">
                    <h4 class="text-muted">No projects yet</h4>
                    <p>Upload a sketch to generate your first web page.</p>
                    <a href="/upload" class="btn btn-primary mt-2">Start a Project</a>
                </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
""",
    "templates/upload.html": """{% extends 'base.html' %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <h2 class="mb-4 text-center">Upload Sketch</h2>
        <div class="card shadow-sm border-0">
            <div class="card-body p-5">
                <form method="POST" action="/upload" enctype="multipart/form-data">
                    <div class="mb-4">
                        <label class="form-label fw-bold">Project Title</label>
                        <input type="text" name="title" class="form-control form-control-lg" placeholder="e.g. Landing Page Form" required>
                    </div>
                    <div class="mb-4">
                        <label class="form-label fw-bold">Sketch Image</label>
                        <div class="upload-dropzone text-center p-5 border rounded" id="dropzone">
                            <i class="fa-solid fa-cloud-arrow-up display-4 text-muted mb-3"></i>
                            <p class="mb-0">Drag and drop your sketch here, or</p>
                            <input type="file" name="sketch" class="form-control mt-3" accept="image/*" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary btn-lg w-100">Generate Code with AI</button>
                </form>
            </div>
        </div>
    </div>
</div>
<style>
.upload-dropzone { border: 2px dashed #ccc !important; background-color: #f8f9fa; }
</style>
{% endblock %}
""",
    "templates/preview.html": """{% extends 'base.html' %}
{% block content %}
<div class="row">
    <div class="col-12 d-flex justify-content-between align-items-center mb-4">
        <h2>{{ project.title }}</h2>
        <a href="/dashboard" class="btn btn-outline-secondary"><i class="fa-solid fa-arrow-left"></i> Back</a>
    </div>
    
    <div class="col-md-6 mb-4">
        <div class="card shadow-sm h-100">
            <div class="card-header bg-dark text-white fw-bold">Original Sketch</div>
            <div class="card-body text-center p-0 bg-light">
                <img src="{{ url_for('static', filename='uploads/' + project.sketch_image_path) }}" class="img-fluid h-100" style="object-fit: contain; max-height: 500px;">
            </div>
        </div>
    </div>
    
    <div class="col-md-6 mb-4">
        <div class="card shadow-sm h-100">
            <div class="card-header bg-primary text-white d-flex justify-content-between">
                <span class="fw-bold">Generated Preview</span>
                <ul class="nav nav-tabs card-header-tabs" role="tablist">
                    <li class="nav-item">
                        <a class="nav-link active text-white border-0 bg-transparent" data-bs-toggle="tab" href="#preview">Preview</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link text-white-50 border-0 bg-transparent" data-bs-toggle="tab" href="#code">Code</a>
                    </li>
                </ul>
            </div>
            <div class="card-body tab-content">
                <div class="tab-pane fade show active" id="preview">
                    <div class="border rounded p-3 h-100 bg-white" style="min-height: 400px; overflow-y: auto;">
                        <iframe id="preview-frame" style="width: 100%; height: 400px; border: none;"></iframe>
                    </div>
                </div>
                <div class="tab-pane fade" id="code">
                    <h6 class="text-muted">HTML</h6>
                    <pre><code class="language-html">{{ project.generated_html }}</code></pre>
                    <h6 class="text-muted mt-3">CSS</h6>
                    <pre><code class="language-css">{{ project.generated_css }}</code></pre>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        var htmlContent = `{{ project.generated_html | safe }}`;
        var cssContent = `<style>{{ project.generated_css | safe }}</style>`;
        var iframe = document.getElementById('preview-frame');
        var head = '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">';
        iframe.contentWindow.document.open();
        iframe.contentWindow.document.write("<html><head>"+head+cssContent+"</head><body>"+htmlContent+"</body></html>");
        iframe.contentWindow.document.close();
    });
</script>
{% endblock %}
""",
    "templates/admin_dashboard.html": """{% extends 'base.html' %}
{% block content %}
<div class="row">
    <div class="col-md-3">
        <div class="list-group shadow-sm mb-4">
            <a href="{{ url_for('admin.dashboard') }}" class="list-group-item list-group-item-action active"><i class="fa-solid fa-chart-line"></i> Admin Dashboard</a>
            <a href="{{ url_for('admin.manage_dataset') }}" class="list-group-item list-group-item-action"><i class="fa-solid fa-database"></i> Managed Dataset</a>
            <form action="{{ url_for('admin.train_model') }}" method="POST" class="d-inline">
                <button type="submit" class="list-group-item list-group-item-action text-primary fw-bold"><i class="fa-solid fa-brain"></i> Train AI Model</button>
            </form>
        </div>
    </div>
    <div class="col-md-9">
        <h2 class="mb-4">System Overview</h2>
        <div class="row">
            <div class="col-md-6 mb-4">
                <div class="card shadow-sm border-primary border-top border-3">
                    <div class="card-body">
                        <h5 class="text-muted">Total Users</h5>
                        <h2 class="display-5 fw-bold">{{ users_count }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-4">
                <div class="card shadow-sm border-success border-top border-3">
                    <div class="card-body">
                        <h5 class="text-muted">Total Generations</h5>
                        <h2 class="display-5 fw-bold">{{ projects_count }}</h2>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""",
    "templates/admin_dataset.html": """{% extends 'base.html' %}
{% block content %}
<div class="row">
    <div class="col-md-3">
        <div class="list-group shadow-sm mb-4">
            <a href="{{ url_for('admin.dashboard') }}" class="list-group-item list-group-item-action"><i class="fa-solid fa-chart-line"></i> Admin Dashboard</a>
            <a href="{{ url_for('admin.manage_dataset') }}" class="list-group-item list-group-item-action active"><i class="fa-solid fa-database"></i> Managed Dataset</a>
        </div>
    </div>
    <div class="col-md-9">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>Dataset Management</h2>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#uploadModal"><i class="fa-solid fa-plus"></i> Upload New Data</button>
        </div>
        
        <div class="card shadow-sm">
            <div class="card-body p-0">
                <table class="table table-hover mb-0">
                    <thead class="bg-light">
                        <tr>
                            <th>Image</th>
                            <th>Label JSON</th>
                            <th>Uploaded By</th>
                            <th>Date</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in datasets %}
                        <tr>
                            <td>{{ item.image_path }}</td>
                            <td>{{ item.label_path }}</td>
                            <td>{{ item.username }}</td>
                            <td>{{ item.created_at }}</td>
                            <td><button class="btn btn-sm btn-outline-danger">Delete</button></td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-center py-4 text-muted">No dataset items found.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="uploadModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Upload Training Data</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" action="{{ url_for('admin.manage_dataset') }}" enctype="multipart/form-data">
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Sketch Image (JPG/PNG)</label>
                        <input type="file" name="image" class="form-control" accept="image/*" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Labels (JSON format)</label>
                        <input type="file" name="labels" class="form-control" accept=".json" required>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-primary">Upload to Dataset</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
""",
    "static/css/style.css": """body {
    background-color: #f8f9fc;
    font-family: 'Inter', sans-serif;
}
.sidebar-link {
    transition: all 0.3s ease;
}
.sidebar-link:hover {
    background-color: #e9ecef;
}
.card {
    border-radius: 12px;
}
""",
    "README.md": """# Sketch2Code GenAI IDE

## Features
- **Backend:** Flask
- **DB:** MySQL
- **Mock AI:** ResNet50 + FPN & Seq2Seq

## Run
1. `pip install -r requirements.txt`
2. `mysql -u root -p < database/schema.sql`
3. `python app.py`

Go to `http://localhost:8000/`
"""
}

# Create directories and write files
workspace_dir = r"z:\s2c"
for filepath, content in files.items():
    full_path = os.path.join(workspace_dir, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# create empty folders
os.makedirs(os.path.join(workspace_dir, r"static\uploads"), exist_ok=True)
os.makedirs(os.path.join(workspace_dir, r"dataset\sketches"), exist_ok=True)
os.makedirs(os.path.join(workspace_dir, r"dataset\labels"), exist_ok=True)
os.makedirs(os.path.join(workspace_dir, r"trained_models"), exist_ok=True)

print("Files created.")
