from models import db, Conversation, Message
from .text_extractor import TextExtractor
import os

class ConversationManager:
    """Handles conversation and message operations"""
    
    @staticmethod
    def save_message(conversation_id, role, content):
        """Save a message to a conversation and return message ID"""
        try:
            print(f"Attempting to save {role} message to conversation {conversation_id}")
            
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                print(f"Conversation {conversation_id} not found!")
                return None
            
            print(f"Found conversation: {conversation.title}")
            
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content
            )
            
            db.session.add(message)
            db.session.flush()  # Flush to get the message ID
            
            message_id = message.id
            print(f"Message saved with ID: {message_id}")
            
            # Update conversation metadata
            current_count = Message.query.filter_by(conversation_id=conversation_id).count()
            conversation.message_count = current_count
            
            # Auto-generate title if it's the first user message and title is generic
            if role == 'user' and ConversationManager._should_update_title(conversation.title):
                new_title = ConversationManager._generate_title_from_content(content)
                conversation.title = new_title
                print(f"Updated conversation title to: {new_title}")
            
            db.session.commit()
            print(f"Successfully saved {role} message")
            return message_id
            
        except Exception as e:
            print(f"Error saving message: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def _should_update_title(current_title):
        """Check if conversation title should be auto-updated"""
        return (current_title == 'New Conversation' or 
                current_title.startswith('Conversation'))
    
    @staticmethod
    def _generate_title_from_content(content):
        """Generate a conversation title from message content"""
        title = content[:50]
        if len(content) > 50:
            title = title.rsplit(' ', 1)[0] + '...'
        return title
    
    @staticmethod
    def build_context_with_attachments(message, attachments):
        """Build enhanced message with file context"""
        if not attachments:
            return message
        
        enhanced_message = message
        file_context = "\n\n--- ATTACHED FILES ---\n"
        
        for attachment in attachments:
            file_path = attachment.get('file_path')
            if file_path and os.path.exists(file_path):
                mime_type = attachment.get('mime_type')
                extracted_text = TextExtractor.extract_text(file_path, mime_type)
                
                file_context += f"\nFile: {attachment.get('original_filename')}\n"
                file_context += f"Type: {mime_type}\n"
                
                if extracted_text:
                    # Truncate text to prevent token overflow
                    truncated_text = TextExtractor.truncate_text(extracted_text, max_chars=4000)
                    file_context += f"Content:\n{truncated_text}\n"
                else:
                    file_context += "Content: [Could not extract text]\n"
                
                file_context += "---\n"
        
        return f"{message}{file_context}"
    
    @staticmethod
    def get_conversation_with_messages(conversation_id):
        """Get conversation with all messages and attachments"""
        try:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return None
            
            return conversation.to_dict(include_messages=True)
        except Exception as e:
            print(f"Error fetching conversation {conversation_id}: {e}")
            return None
    
    @staticmethod
    def delete_conversation(conversation_id):
        """Delete a conversation and all associated data"""
        try:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return False
            
            db.session.delete(conversation)
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting conversation {conversation_id}: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def update_conversation_metadata(conversation_id, **kwargs):
        """Update conversation metadata (title, favorite, archived, etc.)"""
        try:
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                return None
            
            for key, value in kwargs.items():
                if hasattr(conversation, key):
                    setattr(conversation, key, value)
            
            db.session.commit()
            return conversation.to_dict()
        except Exception as e:
            print(f"Error updating conversation {conversation_id}: {e}")
            db.session.rollback()
            return None

