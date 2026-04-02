import os
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
