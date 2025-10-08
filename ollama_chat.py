from flask import Flask, render_template, request, jsonify, Response, send_from_directory, session
import json
import os
import requests
import sys

from utils import *
from models import *

def create_app():
    """Application factory for creating Flask app"""
    app = Flask(__name__)

    # Get data directory from environment or use current directory
    data_dir = os.environ.get('WOOLYCHAT_DATA_DIR', os.getcwd())
    db_path = os.environ.get('WOOLYCHAT_DB_PATH', os.path.join(data_dir, 'ollama_chat.db'))
    uploads_dir = os.environ.get('WOOLYCHAT_UPLOADS_DIR', os.path.join(data_dir, 'uploads'))

    # Configuration
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 5242880 # 5MB limit
    app.config['UPLOAD_FOLDER'] = uploads_dir

    # Ensure upload directory exists
    os.makedirs(uploads_dir, exist_ok=True)
    
    print(f"📁 Using data directory: {data_dir}")
    print(f"📁 Database: {db_path}")
    print(f"📁 Uploads: {uploads_dir}")

    # Ollama base URL
    OLLAMA_BASE_URL = 'http://localhost:11434'

    # Initialize utilities
    file_manager = FileManager(app.config['UPLOAD_FOLDER'], app.config['MAX_CONTENT_LENGTH'])

    def get_theme_css_vars(theme_name):
        """Generate CSS custom properties for a theme"""
        theme = Themes.get_theme(key=theme_name)
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
        current_theme = session.get('theme', Themes.get_default_theme_name())
        return {
            'accent_theme_colors': get_theme_css_vars(current_theme),
            'current_theme': current_theme,
            'available_themes': Themes.get_theme_keys(),
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
            use_artifact = data.get('use_artifact', False)
            
            print(f"Chat request: model={model}, message_len={len(message) if message else 0}, "
                  f"history_len={len(history)}, conv_id={conversation_id}, attachments={len(attachments)}")
            
            # Process attachments to extract images and text
            images_base64 = []
            text_content = message
            
            if attachments:
                file_context, images_base64 = file_manager.process_message_attachements(attachments)
                text_content = f"{message}{file_context}"
            
            if use_artifact:
                 text_content = ARTIFACT_SYSTEM_PROMPT + "\n\n" + text_content

            # Build the user message for Ollama
            user_message = {'role': 'user', 'content': text_content}
            
            # Add images to the message if we have any
            if images_base64:
                user_message['images'] = images_base64
            
            # Format messages for Ollama API
            messages = history + [user_message]
            
            ollama_response = requests.post(
                f'{OLLAMA_BASE_URL}/api/chat',
                json={
                    'model': model,
                    'messages': messages,
                    'stream': True
                },
                stream=True
            )
            
            if ollama_response.status_code != 200:
                error_text = ollama_response.text
                return jsonify({'error': f'Ollama error: {error_text}'}), ollama_response.status_code
            
            def generate():
                assistant_response = ""
                
                for line in ollama_response.iter_lines():
                    if line:
                        try:
                            line_text = line.decode('utf-8')
                            data = json.loads(line_text)
                            if 'message' in data and 'content' in data['message']:
                                content = data['message']['content']
                                if content:
                                    assistant_response += content
                                    yield f'{json.dumps({"content": content})}\n'
                        except (json.JSONDecodeError, Exception) as e:
                            print(f"Error processing line: {e}")
                            continue
                
                # Save conversation with attachments
                if conversation_id and assistant_response and message:
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
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            is_valid, error_message, file_info = file_manager.try_save_file(file)
            if not is_valid:
                return jsonify({'error': error_message}), 400
            
            # Extract text content
            extracted_text = TextExtractor.extract_text(file_info['file_path'], file_info['mime_type'])
            file_info['extracted_text'] = extracted_text

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
            user = User.query.first()
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
            conversation_data = ConversationManager.get_conversation_with_messages(conversation_id)
            
            if not conversation_data:
                return jsonify({'error': 'Conversation not found'}), 404
            
            return jsonify(conversation_data)
        except Exception as e:
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
        current_theme = session.get('theme', Themes.get_default_theme_name())
        return jsonify({
            'current_theme': current_theme,
            'available_themes': list(Themes.get_theme_keys())
        })

    @app.route('/api/settings/theme', methods=['POST'])
    def set_theme():
        """Set theme preference"""
        try:
            data = request.json
            theme_name = data.get('theme')
            
            if theme_name not in Themes.get_theme_keys():
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

    return app

def main():
    """Main entry point when run directly"""
    app = create_app()
    
    # Get port from environment variable (set by launcher) or use default
    port = int(os.environ.get('FLASK_PORT', get_available_port(5000)))
    
    print("Starting WoolyChat - Ollama Chat Interface with Database...")
    print("Make sure Ollama is running on http://localhost:11434")
    print(f"Access the interface at: http://localhost:{port}")
    print(f"Health check available at: http://localhost:{port}/health")
    print("Database file: ollama_chat.db")
    print(f"Upload directory: {app.config['UPLOAD_FOLDER']}")
    
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)

if __name__ == '__main__':
    main()
