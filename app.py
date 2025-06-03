import os
import mimetypes
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from uuid import uuid4
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///secure_share.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload directory exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Generate encryption key if not exists
if not os.path.exists('.key'):
    with open('.key', 'wb') as key_file:
        key_file.write(Fernet.generate_key())

# Load encryption key
with open('.key', 'rb') as key_file:
    KEY = key_file.read()
    FERNET = Fernet(KEY)

# Initialize mimetypes
mimetypes.init()

class File(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    max_downloads = db.Column(db.Integer, nullable=True)
    download_count = db.Column(db.Integer, default=0)
    mime_type = db.Column(db.String(100), nullable=False)

def is_file_expired(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = kwargs.get('token')
        file = File.query.filter_by(token=token).first()
        
        if not file:
            flash('File not found.', 'error')
            return redirect(url_for('index'))
        
        if file.expires_at < datetime.utcnow():
            # Delete expired file
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                db.session.delete(file)
                db.session.commit()
            except Exception as e:
                print(f"Error deleting expired file: {e}")
            flash('This link has expired.', 'error')
            return redirect(url_for('index'))
        
        if file.max_downloads and file.download_count >= file.max_downloads:
            flash('Maximum download limit reached.', 'error')
            return redirect(url_for('index'))
        
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('index'))

    if file:
        # Generate secure filename and save encrypted file
        original_filename = secure_filename(file.filename)
        file_id = str(uuid4())
        extension = os.path.splitext(original_filename)[1]
        filename = f"{file_id}{extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Read and encrypt file content
        file_content = file.read()
        encrypted_content = FERNET.encrypt(file_content)
        
        with open(file_path, 'wb') as f:
            f.write(encrypted_content)
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # Calculate expiration
        expiry_hours = int(request.form.get('expiry_hours', 24))
        max_downloads = request.form.get('max_downloads', type=int)
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # Create database entry
        file_entry = File(
            id=file_id,
            filename=filename,
            original_filename=original_filename,
            token=str(uuid4()),
            expires_at=expires_at,
            max_downloads=max_downloads,
            mime_type=mime_type
        )
        
        db.session.add(file_entry)
        db.session.commit()
        
        download_url = url_for('download_file', token=file_entry.token, _external=True)
        return render_template('success.html', download_url=download_url, expires_at=expires_at)
    
    return redirect(url_for('index'))

@app.route('/download/<token>')
@is_file_expired
def download_file(token):
    file = File.query.filter_by(token=token).first()
    
    if not file:
        flash('File not found.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Read and decrypt file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], file.filename), 'rb') as f:
            encrypted_content = f.read()
        decrypted_content = FERNET.decrypt(encrypted_content)
        
        # Update download count
        file.download_count += 1
        db.session.commit()
        
        # Create temporary file for sending
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{file.filename}")
        with open(temp_path, 'wb') as f:
            f.write(decrypted_content)
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=file.original_filename,
            mimetype=file.mime_type
        )
    except Exception as e:
        flash('Error downloading file.', 'error')
        return redirect(url_for('index'))
    finally:
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 