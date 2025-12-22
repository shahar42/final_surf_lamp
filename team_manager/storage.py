import os
from werkzeug.utils import secure_filename

class LocalStorageService:
    def __init__(self, config):
        self.profiles_dir = config['UPLOAD_FOLDER_PROFILES']
        self.contracts_dir = config['UPLOAD_FOLDER_CONTRACTS']
        self.allowed_extensions = config['ALLOWED_EXTENSIONS']
        
        # Ensure directories exist
        os.makedirs(self.profiles_dir, exist_ok=True)
        os.makedirs(self.contracts_dir, exist_ok=True)

    def is_allowed(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def save_profile(self, file_obj):
        """Saves a profile image and returns the relative URL path."""
        if not file_obj or not file_obj.filename:
            return None
        if not self.is_allowed(file_obj.filename):
            return None
            
        filename = secure_filename(file_obj.filename)
        filepath = os.path.join(self.profiles_dir, filename)
        file_obj.save(filepath)
        # Return path suitable for 'static' url building or direct access if served as static
        # Logic from app.py: "uploads/profiles/{filename}"
        return f'uploads/profiles/{filename}'

    def save_contract(self, file_obj):
        """Saves a contract PDF and returns the filename."""
        if not file_obj or not file_obj.filename:
            return None
        if not self.is_allowed(file_obj.filename):
            return None
            
        filename = secure_filename(file_obj.filename)
        filepath = os.path.join(self.contracts_dir, filename)
        file_obj.save(filepath)
        return filename

    def delete_contract(self, filename):
        """Deletes a contract file."""
        if not filename:
            return
        filepath = os.path.join(self.contracts_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
