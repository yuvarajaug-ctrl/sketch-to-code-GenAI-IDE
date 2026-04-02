import os
import sys

# Force UTF-8 output so Unicode chars in print() never crash on Windows cp1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()
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
