import os

class TextExtractor:
    """Handles text extraction from various file types"""
    
    @staticmethod
    def extract_text(file_path, mime_type):
        """Extract text content from uploaded files"""
        try:
            if mime_type == 'text/plain' or mime_type == 'text/markdown':
                return TextExtractor._extract_plain_text(file_path)
            
            elif mime_type == 'application/pdf':
                return TextExtractor._extract_pdf_text(file_path)
            
            elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return TextExtractor._extract_word_text(file_path)
            
            elif mime_type.startswith('image/'):
                return TextExtractor._handle_image_file(file_path)
            
            elif mime_type == 'text/csv':
                return TextExtractor._extract_csv_preview(file_path)
            
            elif mime_type == 'application/json':
                return TextExtractor._extract_json_content(file_path)
            
            elif mime_type in ['text/html', 'text/xml']:
                return TextExtractor._extract_markup_content(file_path)
            
            else:
                return f"[File: {os.path.basename(file_path)} - Content type not supported for text extraction]"
                
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return f"[File: {os.path.basename(file_path)} - Error reading file: {str(e)}]"
    
    @staticmethod
    def _extract_plain_text(file_path):
        """Extract text from plain text files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def _extract_pdf_text(file_path):
        """Extract text from PDF files"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except ImportError:
            print("PyPDF2 not installed, cannot extract PDF text")
            return f"[PDF file: {os.path.basename(file_path)} - Install PyPDF2 for text extraction]"
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return f"[PDF file: {os.path.basename(file_path)} - Error extracting text: {str(e)}]"
    
    @staticmethod
    def _extract_word_text(file_path):
        """Extract text from Word documents"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except ImportError:
            print("python-docx not installed, cannot extract Word document text")
            return f"[Word document: {os.path.basename(file_path)} - Install python-docx for text extraction]"
        except Exception as e:
            print(f"Error extracting Word document text: {e}")
            return f"[Word document: {os.path.basename(file_path)} - Error extracting text: {str(e)}]"
    
    @staticmethod
    def _handle_image_file(file_path):
        """Handle image files (placeholder for future OCR)"""
        return f"[Image file: {os.path.basename(file_path)}]"
    
    @staticmethod
    def _extract_csv_preview(file_path):
        """Extract preview of CSV files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first few lines as preview
            lines = f.readlines()[:10]
            return ''.join(lines)
    
    @staticmethod
    def _extract_json_content(file_path):
        """Extract content from JSON files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def _extract_markup_content(file_path):
        """Extract content from HTML/XML files"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def truncate_text(text, max_chars=4000):
        """Truncate text to prevent token overflow"""
        if not text or len(text) <= max_chars:
            return text
        
        return text[:max_chars] + "\n... [truncated]"
