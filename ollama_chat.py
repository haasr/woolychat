from flask import Flask, render_template, request, jsonify, Response, send_from_directory, session
import base64
import json
import os
import requests

from utils import *
from models import *

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ollama_chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 5242880 # 5MB limit
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ollama base URL
OLLAMA_BASE_URL = 'http://localhost:11434'

# Initialize utilities
file_manager = FileManager(app.config['UPLOAD_FOLDER'], app.config['MAX_CONTENT_LENGTH'])

# Theme definitions
THEMES = {
    'ocean_breeze': {
        'header_gradient_left': '#72dddd',
        'header_gradient_right': '#86c3f9',
        'bg_gradient_left': '#60c1e7',
        'bg_gradient_right': '#7fc9e2'
    },
    'golden': {
        'header_gradient_left': '#e9a508',
        'header_gradient_right': '#ffcb46',
        'bg_gradient_left': '#1362b1',
        'bg_gradient_right': '#52a1ef'
    },
    'autumn': {
        'header_gradient_left': '#cd5a08',
        'header_gradient_right': '#f98a3a',
        'bg_gradient_left': '#703d39',
        'bg_gradient_right': '#a13670'
    },
    'midnight': {
        'header_gradient_left': '#283593',
        'header_gradient_right': '#3a0080',
        'bg_gradient_left': '#10105c',
        'bg_gradient_right': '#2d2d8a'
    },
    'cyberpunk': {
        'header_gradient_left': '#9c27b0',
        'header_gradient_right': '#e91e63',
        'bg_gradient_left': '#16a0a0',
        'bg_gradient_right': '#494949'
    },
    'vinyl': {
        'header_gradient_left': '#b71c1c',
        'header_gradient_right': '#cc0000',
        'bg_gradient_left': '#333333',
        'bg_gradient_right': '#444444'
    },
    'koala': {
        'header_gradient_left': '#8d9db6',
        'header_gradient_right': '#a8b5c8',
        'bg_gradient_left': '#7d8471',
        'bg_gradient_right': '#9db4a0'
    },
    'pink': {
        'header_gradient_left': '#FF69B4',
        'header_gradient_right': '#FF81A6',
        'bg_gradient_left': '#F48FB1',
        'bg_gradient_right': '#E9967A'
    },
    'forest': {
        'header_gradient_left': '#3a8673',
        'header_gradient_right': '#2d6a4f',
        'bg_gradient_left': '#2d6a4f',
        'bg_gradient_right': '#3a8658'
    },
    'moonlit_lilac': {
        'header_gradient_left': '#667eea',
        'header_gradient_right': '#764ba2',
        'bg_gradient_left': '#1e3a8a',
        'bg_gradient_right': '#294a8b'
    },
    'summer_sunset': {
        'header_gradient_left': '#e9c46a',
        'header_gradient_right': '#f4a261',
        'bg_gradient_left': "#f16236",
        'bg_gradient_right': "#ee952f"
    },
    'ryan': {
        'header_gradient_left': "#e3b84b",
        'header_gradient_right': "#e6bd57",
        'bg_gradient_left': "#37764a",
        'bg_gradient_right': "#0c9186"
    },
    'zebra': {
        'header_gradient_left': '#212121',
        'header_gradient_right': '#24293b',
        'bg_gradient_left': '#1e2936',
        'bg_gradient_right': '#28303f'
    }
}

DEFAULT_THEME = 'zebra'

def get_theme_css_vars(theme_name):
    """Generate CSS custom properties for a theme"""
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    return f"""
        --header-gradient-left: {theme['header_gradient_left']};
        --header-gradient-right: {theme['header_gradient_right']};
        --bg-gradient-left: {theme['bg_gradient_left']};
        --bg-gradient-right: {theme['bg_gradient_right']};
    """

# Initialize database
init_db(app)

# Context processor
@app.context_processor
def inject_theme():
    """Inject theme variables into all templates"""
    current_theme = session.get('theme', DEFAULT_THEME)
    return {
        'accent_theme_colors': get_theme_css_vars(current_theme),
        'current_theme': current_theme,
        'available_themes': THEMES.keys()
    }

# ==== MAIN ROUTES ====
@app.route('/')
def index():
    """Serve the chat interface"""
    return render_template('index.html')

# ==== OLLAMA PROXY ENDPOINTS ====
@app.route('/api/tags')
def get_models():
    """Proxy endpoint to get available Ollama models"""
    try:
        response = requests.get(f'{OLLAMA_BASE_URL}/api/tags')
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Proxy endpoint for streaming chat with Ollama"""
    try:
        data = request.json
        model = data.get('model')
        message = data.get('message')
        history = data.get('history', [])
        conversation_id = data.get('conversation_id')
        attachments = data.get('attachments', [])
        
        print(f"Chat request: model={model}, message_len={len(message) if message else 0}, "
              f"history_len={len(history)}, conv_id={conversation_id}, attachments={len(attachments)}")
        
        # Debug: Print attachment details
        for i, att in enumerate(attachments):
            print(f"Attachment {i}: {att.get('original_filename')} - {att.get('mime_type')} - Path: {att.get('file_path')}")
        
        # Process attachments to extract images and text
        images_base64 = []
        text_content = message
        
        if attachments:
            file_context = "\n\n--- ATTACHED FILES ---\n"
            
            for attachment in attachments:
                file_path = attachment.get('file_path')
                mime_type = attachment.get('mime_type')
                original_filename = attachment.get('original_filename')
                
                print(f"Processing attachment: {original_filename} at {file_path}")
                
                if file_path and os.path.exists(file_path):
                    print(f"File exists: {file_path}")
                    
                    if mime_type.startswith('image/'):
                        # Convert image to base64 for Ollama
                        try:
                            with open(file_path, 'rb') as img_file:
                                img_data = img_file.read()
                                img_base64 = base64.b64encode(img_data).decode('utf-8')
                                images_base64.append(img_base64)
                                print(f"Successfully encoded image: {original_filename} ({len(img_base64)} chars)")
                        except Exception as e:
                            print(f"Error encoding image {file_path}: {e}")
                    else:
                        # For non-image files, extract text content
                        extracted_text = TextExtractor.extract_text(file_path, mime_type)
                        if extracted_text:
                            file_context += f"\nFile: {original_filename}\n"
                            file_context += f"Type: {mime_type}\n"
                            truncated_text = TextExtractor.truncate_text(extracted_text, max_chars=4000)
                            file_context += f"Content:\n{truncated_text}\n---\n"
                else:
                    print(f"File does not exist: {file_path}")
            
            # Add file context only if there were non-image files
            if "File:" in file_context:
                text_content = f"{message}{file_context}"
        
        # Build the user message for Ollama
        user_message = {'role': 'user', 'content': text_content}
        
        # Add images to the message if we have any
        if images_base64:
            user_message['images'] = images_base64
            print(f"Sending {len(images_base64)} images to Ollama (first image: {len(images_base64[0])} chars)")
        
        # Format messages for Ollama API
        messages = history + [user_message]
        
        print(f"Sending to Ollama: model={model}, messages={len(messages)}, images={len(images_base64)}")
        
        # Debug: Print the actual request being sent to Ollama
        ollama_request_data = {
            'model': model,
            'messages': messages,
            'stream': True
        }
        
        print(f"Ollama request structure: model={model}, message_count={len(messages)}, has_images={bool(images_base64)}")
        
        ollama_response = requests.post(
            f'{OLLAMA_BASE_URL}/api/chat',
            json=ollama_request_data,
            stream=True
        )
        
        print(f"Ollama response status: {ollama_response.status_code}")
        
        # If there's an error, print the response
        if ollama_response.status_code != 200:
            error_text = ollama_response.text
            print(f"Ollama error response: {error_text}")
            return jsonify({'error': f'Ollama error: {error_text}'}), ollama_response.status_code
        
        def generate():
            content_sent = False
            assistant_response = ""
            
            for line in ollama_response.iter_lines():
                if line:
                    try:
                        line_text = line.decode('utf-8')
                        data = json.loads(line_text)
                        if 'message' in data and 'content' in data['message']:
                            content = data['message']['content']
                            if content:
                                content_sent = True
                                assistant_response += content
                                yield f'{json.dumps({"content": content})}\n'
                    except (json.JSONDecodeError, Exception) as e:
                        print(f"Error processing line: {e}")
                        continue
            
            # Save conversation with attachments
            if conversation_id and assistant_response and message:
                print(f"Saving messages with {len(attachments)} attachments")
                
                with app.app_context():
                    try:
                        # Save user message
                        user_message_id = ConversationManager.save_message(conversation_id, 'user', message)
                        
                        # Save attachments to database
                        if user_message_id and attachments:
                            file_manager.save_multiple_attachments(user_message_id, attachments)
                        
                        # Save assistant response
                        ConversationManager.save_message(conversation_id, 'assistant', assistant_response)
                        
                    except Exception as e:
                        print(f"Error saving messages with attachments: {e}")
            
            if not content_sent:
                print("No content was sent!")
        
        return Response(generate(), mimetype='text/plain')
        
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        print(f"Unexpected error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==== FILE UPLOAD ENDPOINTS ====
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload for message attachments"""
    try:
        print("File upload request received")
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get file info
        original_filename = file.filename
        
        # Read file to get size
        file_content = file.read()
        file_size = len(file_content)
        file.seek(0)  # Reset file pointer
        
        # Get MIME type
        mime_type = file_manager.get_mime_type(original_filename)
        
        print(f"File info: {original_filename}, {file_manager.format_file_size(file_size)}, {mime_type}")
        
        # Validate file
        is_valid, error_message = file_manager.validate_file(original_filename, mime_type, file_size)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Generate unique filename and save
        unique_filename = file_manager.generate_unique_filename(original_filename)
        file_path = file_manager.save_file(file, unique_filename)
        
        print(f"File saved to: {file_path}")
        
        # Extract text content
        extracted_text = TextExtractor.extract_text(file_path, mime_type)
        
        # Return file info
        file_info = {
            'id': unique_filename,
            'original_filename': original_filename,
            'filename': unique_filename,
            'file_size': file_size,
            'file_size_str': file_manager.format_file_size(file_size),
            'mime_type': mime_type,
            'file_path': file_path,
            'has_text': bool(extracted_text),
            'text_preview': extracted_text[:200] + '...' if extracted_text and len(extracted_text) > 200 else extracted_text,
            'extracted_text': extracted_text  # Include for saving to DB later
        }
        
        print(f"Upload successful: {file_info}")
        return jsonify(file_info), 200
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<filename>')
def serve_file(filename):
    """Serve uploaded files"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# ==== CONVERSATION MANAGEMENT ENDPOINTS ====
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for the current user"""
    try:
        user = User.query.first()  # For now, just use first user
        conversations = Conversation.query.filter_by(
            user_id=user.id, 
            is_archived=False
        ).order_by(Conversation.updated_at.desc()).all()
        
        return jsonify([conv.to_dict() for conv in conversations])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.json
        user = User.query.first()
        
        conversation = Conversation(
            title=data.get('title', 'New Conversation'),
            model_name=data.get('model_name', ''),
            user_id=user.id
        )
        
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify(conversation.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation with messages"""
    try:
        print(f"Fetching conversation {conversation_id}")
        conversation_data = ConversationManager.get_conversation_with_messages(conversation_id)
        
        if not conversation_data:
            return jsonify({'error': 'Conversation not found'}), 404
        
        print(f"Returning conversation with {len(conversation_data.get('messages', []))} messages")
        return jsonify(conversation_data)
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """Update conversation metadata"""
    try:
        data = request.json
        result = ConversationManager.update_conversation_metadata(conversation_id, **data)
        
        if not result:
            return jsonify({'error': 'Conversation not found or update failed'}), 404
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        success = ConversationManager.delete_conversation(conversation_id)
        if success:
            return jsonify({'message': 'Conversation deleted'})
        else:
            return jsonify({'error': 'Failed to delete conversation'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==== TAG MANAGEMENT ====
@app.route('/api/tags', methods=['GET'])
def get_tags():
    """Get all tags"""
    try:
        tags = Tag.query.all()
        return jsonify([tag.to_dict() for tag in tags])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags', methods=['POST'])
def create_tag():
    """Create a new tag"""
    try:
        data = request.json
        tag = Tag(
            name=data['name'],
            color=data.get('color', '#6c757d')
        )
        db.session.add(tag)
        db.session.commit()
        return jsonify(tag.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==== PROJECT MANAGEMENT ====
@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all projects for the current user"""
    try:
        user = User.query.first()
        projects = Project.query.filter_by(user_id=user.id).all()
        return jsonify([project.to_dict() for project in projects])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.json
        user = User.query.first()
        
        project = Project(
            name=data['name'],
            description=data.get('description', ''),
            color=data.get('color', '#667eea'),
            user_id=user.id
        )
        
        db.session.add(project)
        db.session.commit()
        return jsonify(project.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==== SETTINGS ENDPOINTS ====
@app.route('/api/settings/theme', methods=['GET'])
def get_theme():
    """Get current theme setting"""
    current_theme = session.get('theme', DEFAULT_THEME)
    return jsonify({
        'current_theme': current_theme,
        'available_themes': list(THEMES.keys())
    })

@app.route('/api/settings/theme', methods=['POST'])
def set_theme():
    """Set theme preference"""
    try:
        data = request.json
        theme_name = data.get('theme')
        
        if theme_name not in THEMES:
            return jsonify({'error': 'Invalid theme'}), 400
        
        session['theme'] = theme_name
        return jsonify({'success': True, 'theme': theme_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==== UTILITY ENDPOINTS ====
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        response = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=5)
        ollama_status = 'connected' if response.status_code == 200 else 'disconnected'
    except:
        ollama_status = 'disconnected'
    
    # Check database
    try:
        user_count = User.query.count()
        db_status = 'connected'
    except:
        db_status = 'disconnected'
        user_count = 0
    
    return jsonify({
        'flask': 'running',
        'ollama': ollama_status,
        'database': db_status,
        'users': user_count,
        'ollama_url': OLLAMA_BASE_URL,
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'max_file_size': file_manager.format_file_size(app.config['MAX_CONTENT_LENGTH'])
    })

if __name__ == '__main__':
    available_port = get_available_port(5000)

    print("Starting WoolyChat - Ollama Chat Interface with Database...")
    print("Make sure Ollama is running on http://localhost:11434")
    print(f"Access the interface at: http://localhost:{available_port}")
    print(f"Health check available at: http://localhost:{available_port}/health")
    print("Database file: ollama_chat.db")
    print(f"Upload directory: {app.config['UPLOAD_FOLDER']}")
    print(f"Max file size: {file_manager.format_file_size(app.config['MAX_CONTENT_LENGTH'])}")

    app.run(debug=True, host='0.0.0.0', port=available_port)