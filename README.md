# Secure File Sharing with Expiring Links

A secure file sharing application that allows users to upload files and generate time-limited or usage-limited download links. Files are encrypted using AES-256 encryption and automatically deleted after expiration.

## Features

- Secure file upload with AES-256 encryption
- Time-based and usage-based expiring download links
- Automatic file cleanup after expiration
- Simple and intuitive web interface
- File metadata tracking using SQLite

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with the following content:
   ```
   SECRET_KEY=your-secret-key-here
   UPLOAD_FOLDER=uploads
   DATABASE_URL=sqlite:///secure_share.db
   ```
5. Initialize the database:
   ```bash
   python init_db.py
   ```
6. Run the application:
   ```bash
   python app.py
   ```

## Security Considerations

- All files are encrypted using Fernet (AES-256)
- Download links are tokenized and unguessable
- Files are automatically deleted after expiration
- Encryption keys are stored securely in environment variables

## Usage

1. Visit the homepage and upload a file
2. Set expiration parameters (time or number of downloads)
3. Share the generated download link
4. Recipients can download the file until it expires

## License

MIT License 