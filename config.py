
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-sketch2code'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'sketch2code_db'
    
    basedir = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    DATASET_FOLDER = os.path.join(basedir, 'dataset')
    TRAINED_MODELS_FOLDER = os.path.join(basedir, 'trained_models')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
