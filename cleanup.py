import os
from datetime import datetime
from app import app, db, File

def cleanup_expired_files():
    with app.app_context():
        # Find all expired files
        expired_files = File.query.filter(File.expires_at < datetime.utcnow()).all()
        
        for file in expired_files:
            try:
                # Delete the file from storage
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Delete the database entry
                db.session.delete(file)
                
            except Exception as e:
                print(f"Error cleaning up file {file.filename}: {e}")
        
        # Commit all changes
        db.session.commit()
        
        print(f"Cleaned up {len(expired_files)} expired files")

if __name__ == '__main__':
    cleanup_expired_files() 