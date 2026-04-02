import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from werkzeug.utils import secure_filename
import json
from inference import extract_elements, generate_code_from_elements
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
            
            # Save Initial Project to DB
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO projects (user_id, title, sketch_image_path) VALUES (%s, %s, %s)",
                    (session['user_id'], title, filename)
                )
                conn.commit()
                project_id = cursor.lastrowid
                conn.close()
                return redirect(url_for('main.detect', project_id=project_id))
            else:
                flash('Database error while saving.', 'danger')
                
    return render_template('upload.html')

@main_bp.route('/detect/<int:project_id>')
def detect(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    conn = get_db_connection()
    if not conn:
        flash("DB connection error", "danger")
        return redirect(url_for('main.dashboard'))
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE id = %s AND user_id = %s", (project_id, session['user_id']))
    project = cursor.fetchone()
    
    if not project:
        conn.close()
        flash("Project not found", "danger")
        return redirect(url_for('main.dashboard'))
        
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], project['sketch_image_path'])
    
    # Extract Elements
    extraction_data = extract_elements(filepath)
    elements_json = json.dumps(extraction_data.get('elements', extraction_data) if isinstance(extraction_data, dict) else extraction_data)
    page_type = extraction_data.get('page_type', 'form') if isinstance(extraction_data, dict) else 'form'
    
    try:
        elements = json.loads(elements_json)
    except Exception:
        elements = []
        
    # Generate code from the extracted elements directly
    html_code, css_code, java_code = generate_code_from_elements(elements, page_type=page_type)
    
    # Save Java code to a file as required
    java_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], "GeneratedController.java")
    with open(java_filepath, 'w') as f:
        f.write(java_code)

    # Save Elements to DB
    cursor.execute(
        "UPDATE projects SET detected_elements = %s, generated_html = %s, generated_css = %s, generated_java = %s, page_type = %s WHERE id = %s",
        (elements_json, html_code, css_code, java_code, page_type, project_id)
    )
    conn.commit()
    conn.close()
    
    flash("Project processed and code generated successfully!", "success")
    return redirect(url_for('main.preview', project_id=project_id))


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
        
    elements = []
    if project.get('detected_elements'):
        try:
            elements = json.loads(project['detected_elements'])
        except Exception:
            pass
            
    return render_template('preview.html', project=project, elements=elements)

@main_bp.route('/api/generate_code', methods=['POST'])
def api_generate_code():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    project_id = data.get('project_id')
    elements = data.get('elements', [])
    page_type = data.get('page_type', 'form')
    
    html_code, css_code, java_code = generate_code_from_elements(elements, page_type=page_type)
    
    # Save to db if project_id is provided
    if project_id:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET detected_elements = %s, generated_html = %s, generated_css = %s, generated_java = %s, page_type = %s WHERE id = %s",
                (json.dumps(elements), html_code, css_code, java_code, page_type, project_id)
            )
            conn.commit()
            conn.close()
            
    return jsonify({
        "html": html_code,
        "css": css_code,
        "java": java_code
    })

@main_bp.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    conn = get_db_connection()
    if not conn:
        flash("DB connection error", "danger")
        return redirect(url_for('main.dashboard'))
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE id = %s AND user_id = %s", (project_id, session['user_id']))
    project = cursor.fetchone()
    
    if project:
        # Delete file
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], project['sketch_image_path'])
        if os.path.exists(filepath):
            os.remove(filepath)
            
        # Delete from DB
        cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        conn.commit()
        flash("Project deleted successfully.", "success")
    else:
        flash("Project not found.", "danger")
        
    conn.close()
    return redirect(url_for('main.dashboard'))

