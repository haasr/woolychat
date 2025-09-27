from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Text, JSON
from typing import List, Optional

db = SQLAlchemy()

# Association tables for many-to-many relationships
conversation_tags = db.Table('conversation_tags',
    db.Column('conversation_id', db.Integer, db.ForeignKey('conversation.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

project_conversations = db.Table('project_conversations',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('conversation_id', db.Integer, db.ForeignKey('conversation.id'), primary_key=True)
)

class User(db.Model):
    """User model - keeping simple for now, can expand later"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, default='admin')
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='user', lazy=True)
    projects = db.relationship('Project', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    """Project model - top-level organization with file storage"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(Text, nullable=True)
    color = db.Column(db.String(7), default='#667eea')  # Hex color for UI
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Settings/configuration as JSON
    settings = db.Column(JSON, default=dict)
    
    # Relationships
    conversations = db.relationship('Conversation', secondary=project_conversations, 
                                  back_populates='projects', lazy='dynamic')
    files = db.relationship('ProjectFile', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'created_at': self.created_at.isoformat(),
            'conversation_count': self.conversations.count(),
            'file_count': len(self.files)
        }

class Conversation(db.Model):
    """Conversation model - represents a chat session"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Conversation metadata
    message_count = db.Column(db.Integer, default=0)
    is_archived = db.Column(db.Boolean, default=False)
    is_favorite = db.Column(db.Boolean, default=False)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, 
                             cascade='all, delete-orphan', order_by='Message.created_at')

    tags = db.relationship('Tag', secondary=conversation_tags, back_populates='conversations')
    projects = db.relationship('Project', secondary=project_conversations, back_populates='conversations')

    @property
    def all_attachments(self):
        """Get all attachments from all messages in this conversation"""
        attachments = []
        for message in self.messages:
            attachments.extend(message.attachments)
        return attachments

    def __repr__(self):
        return f'<Conversation {self.title}>'
    
    def to_dict(self, include_messages=False):
        data = {
            'id': self.id,
            'title': self.title,
            'model_name': self.model_name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': self.message_count,
            'is_archived': self.is_archived,
            'is_favorite': self.is_favorite,
            'tags': [tag.to_dict() for tag in self.tags],
            'projects': [{'id': p.id, 'name': p.name, 'color': p.color} for p in self.projects]
        }
        if include_messages:
            data['messages'] = [msg.to_dict() for msg in self.messages]
            
        return data
    
    def generate_title(self):
        """Auto-generate title from first user message"""
        first_message = Message.query.filter_by(
            conversation_id=self.id, 
            role='user'
        ).first()
        
        if first_message:
            # Take first 50 chars, cut at word boundary
            title = first_message.content[:50]
            if len(first_message.content) > 50:
                title = title.rsplit(' ', 1)[0] + '...'
            return title
        return f'Conversation {self.id}'

class Message(db.Model):
    """Message model - individual messages in conversations"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    attachments = db.relationship('MessageAttachment', backref='message', lazy=True, 
                            cascade='all, delete-orphan')

    # Optional metadata
    message_metadata = db.Column(JSON, default=dict)  # For storing extra info like tokens, processing time, etc.
    
    def __repr__(self):
        return f'<Message {self.role}: {self.content[:50]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'message_metadata': self.message_metadata or {},
            'attachments': [att.to_dict() for att in self.attachments]
        }

class MessageAttachment(db.Model):
    """File attachments for messages"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # File content for AI context
    extracted_text = db.Column(Text, nullable=True)  # Extracted text content
    is_processed = db.Column(db.Boolean, default=False)
    processing_error = db.Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<MessageAttachment {self.original_filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'uploaded_at': self.uploaded_at.isoformat(),
            'is_processed': self.is_processed,
            'has_text': bool(self.extracted_text)
        }

class Tag(db.Model):
    """Tag model - unstructured tags for organizing conversations"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', secondary=conversation_tags, back_populates='tags')
    
    def __repr__(self):
        return f'<Tag {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'conversation_count': len(self.conversations)
        }

class ProjectFile(db.Model):
    """File model - files associated with projects for knowledge injection"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For future vector search capabilities
    is_processed = db.Column(db.Boolean, default=False)
    processing_error = db.Column(Text, nullable=True)
    
    # File content metadata
    content_preview = db.Column(Text, nullable=True)  # First few hundred chars
    file_metadata = db.Column(JSON, default=dict)  # File-specific metadata
    
    def __repr__(self):
        return f'<ProjectFile {self.original_filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'uploaded_at': self.uploaded_at.isoformat(),
            'is_processed': self.is_processed,
            'content_preview': self.content_preview
        }

def init_db(app):
    """Initialize database with app context"""
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # Create default user if none exists
        if not User.query.first():
            default_user = User(username='admin', email='admin@localhost')
            db.session.add(default_user)
            db.session.commit()
            print("Created default user: admin")
        
        print("Database initialized successfully!")
