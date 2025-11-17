import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "surya_secret_key")
    
    # SQLite database for simple usage
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///surya.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Folder to store generated PDFs
    PDF_FOLDER = os.path.join(os.getcwd(), "pdf_reports")
    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER)
      
