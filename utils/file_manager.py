import os
import uuid
import mimetypes
import math
from werkzeug.utils import secure_filename
from models import db, MessageAttachment

class FileManager:
    """Handles file upload, validation, and storage operations"""
    
    def __init__(self, upload_folder, max_file_size=5242880): # Max file size = 5MB
        self.upload_folder = upload_folder
        self.max_file_size = max_file_size
        
        # Allowed file types
        self.allowed_extensions = {
            'txt', 'pdf', 'doc', 'docx', 'md', 'rtf',  # Text documents
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',  # Images
            'csv', 'xlsx', 'xls',  # Data files
            'json', 'xml', 'html', 'htm'  # Structured data
        }
        
        self.allowed_mime_types = {
            'text/plain', 'text/markdown', 'text/csv', 'text/html', 'text/xml',
            'application/pdf', 'application/json',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
        }

        # Ensure upload directory exists
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def validate_file(self, filename, mimetype, file_size):
        """Validate file based on extension, MIME type, and size"""
        if not filename:
            return False, "No filename provided"
        
        # Check file size
        if file_size > self.max_file_size:
            return False, f"File too large. Maximum size is {self.format_file_size(self.max_file_size)}"
        
        # Check extension
        extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if extension not in self.allowed_extensions:
            return False, f"File type not allowed. Supported types: {', '.join(sorted(self.allowed_extensions))}"
        
        # Check MIME type
        if mimetype not in self.allowed_mime_types:
            return False, f"MIME type not allowed: {mimetype}"
        
        return True, "Valid"
    
    def get_mime_type(self, filename):
        """Get MIME type from filename with fallback"""
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            mime_type = self._get_mime_type_from_extension(ext)
        return mime_type
    
    def _get_mime_type_from_extension(self, ext):
        """Get MIME type from file extension as fallback"""
        mime_map = {
            'txt': 'text/plain',
            'md': 'text/markdown',
            'csv': 'text/csv',
            'json': 'application/json',
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'webp': 'image/webp',
            'html': 'text/html',
            'htm': 'text/html',
            'xml': 'text/xml',
            'rtf': 'application/rtf'
        }
        return mime_map.get(ext, 'application/octet-stream')
    
    def generate_unique_filename(self, original_filename):
        """Generate a unique filename while preserving extension"""
        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else uuid.uuid4().hex
        return unique_filename
    
    def save_file(self, file, filename):
        """Save file to upload directory"""
        file_path = os.path.join(self.upload_folder, filename)
        file.save(file_path)
        return file_path
    
    def delete_file(self, filename):
        """Delete file from upload directory"""
        try:
            file_path = os.path.join(self.upload_folder, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
        return False
    
    def save_attachment_to_db(self, message_id, file_info, extracted_text=None):
        """Save file attachment info to database"""
        try:
            attachment = MessageAttachment(
                message_id=message_id,
                filename=file_info['filename'],
                original_filename=file_info['original_filename'],
                file_path=file_info['file_path'],
                file_size=file_info['file_size'],
                mime_type=file_info['mime_type'],
                extracted_text=extracted_text,
                is_processed=bool(extracted_text)
            )
            
            db.session.add(attachment)
            db.session.commit()
            return attachment
        except Exception as e:
            print(f"Error saving attachment to database: {e}")
            db.session.rollback()
            return None
    
    def save_multiple_attachments(self, message_id, attachments_data):
        """Save multiple file attachments for a message"""
        try:
            saved_attachments = []
            for attachment_data in attachments_data:
                attachment = MessageAttachment(
                    message_id=message_id,
                    filename=attachment_data.get('filename'),
                    original_filename=attachment_data.get('original_filename'),
                    file_path=attachment_data.get('file_path'),
                    file_size=attachment_data.get('file_size'),
                    mime_type=attachment_data.get('mime_type'),
                    extracted_text=attachment_data.get('extracted_text'),
                    is_processed=bool(attachment_data.get('extracted_text'))
                )
                db.session.add(attachment)
                saved_attachments.append(attachment)
            
            db.session.commit()
            print(f"Saved {len(saved_attachments)} attachments for message {message_id}")
            return saved_attachments
        except Exception as e:
            print(f"Error saving attachments: {e}")
            db.session.rollback()
            return []
    
    @staticmethod
    def format_file_size(bytes_size):
        """Convert bytes to human readable format"""
        if bytes_size == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = int(math.floor(math.log(bytes_size, 1024)))
        p = math.pow(1024, i)
        s = round(bytes_size / p, 2)
        return f"{s} {size_names[i]}"
