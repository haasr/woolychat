class OllamaChat {
    constructor() {
        this.baseUrl = '/api';
        this.currentModel = '';
        this.conversationHistory = [];
        this.currentConversationId = null;
        this.conversations = [];
        
        // Configure marked to open links in new tabs
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                renderer: new marked.Renderer(),
                breaks: true,
                gfm: true
            });
            
            // Override link renderer to add target="_blank"
            const renderer = new marked.Renderer();
            renderer.link = function(href, title, text) {
                return `<a href="${href}" target="_blank" rel="noopener noreferrer"${title ? ` title="${title}"` : ''}>${text}</a>`;
            };
            marked.setOptions({ renderer });
        }

        // File upload properties
        this.pendingAttachments = [];
        this.maxFileSize = 5242880; // 5MB
        this.allowedTypes = [
            'text/plain', 'text/markdown', 'text/csv', 'text/html', 'text/xml',
            'application/pdf', 'application/json',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
        ];

        this.applySettings();
        this.initializeElements();
        this.setupEventListeners();
        this.initializeSidebarState();
        this.checkConnection();
        this.loadModels();
        this.loadConversations();
    }

    initializeElements() {
        // Chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.modelSelect = document.getElementById('modelSelect');
        this.refreshModels = document.getElementById('refreshModels');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.chatForm = document.getElementById('chatForm');
        
        // Sidebar elements
        this.sidebar = document.getElementById('sidebar');
        this.conversationsList = document.getElementById('conversationsList');
        this.newConversationBtn = document.getElementById('newConversationBtn');
        this.toggleSidebar = document.getElementById('toggleSidebar');
        this.sidebarToggleCollapsed = document.getElementById('sidebarToggleCollapsed');
        this.toggleSidebarCollapsedBtn = document.getElementById('toggleSidebarCollapsedBtn');
        this.mobileMenuBtn = document.getElementById('mobileMenuBtn');
        this.sidebarOverlay = document.getElementById('sidebarOverlay');
    
        // Settings elements
        this.appSettings = document.getElementById('appSettings');
        this.settingsModal = document.getElementById('settingsModal');
        this.closeSettings = document.getElementById('closeSettings');
        this.themeSelect = document.getElementById('themeSelect');
        this.themePreview = document.getElementById('themePreview');
        this.saveSettings = document.getElementById('saveSettings');
        this.resetSettings = document.getElementById('resetSettings');
        this.markdownEnabled = document.getElementById('markdownEnabled');
        this.autoScrollEnabled = document.getElementById('autoScrollEnabled');
    
        // File upload elements
        this.attachFileBtn = document.getElementById('attachFileBtn');
        this.fileInput = document.getElementById('fileInput');
        this.attachmentsPreview = document.getElementById('attachmentsPreview');
        this.attachmentsList = document.getElementById('attachmentsList');
        this.clearAttachments = document.getElementById('clearAttachments');
    
        // File upload listeners
        this.attachFileBtn.addEventListener('click', () => this.triggerFileInput());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.clearAttachments.addEventListener('click', () => this.clearAllAttachments());
        
        // Drag and drop support
        this.chatMessages.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.chatMessages.addEventListener('drop', (e) => this.handleDrop(e));
        this.chatMessages.addEventListener('dragleave', (e) => this.handleDragLeave(e));
    }

    setupEventListeners() {
        // Chat form
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.modelSelect.addEventListener('change', (e) => this.handleModelChange(e));
        this.refreshModels.addEventListener('click', () => this.loadModels());
        
        // Sidebar
        this.newConversationBtn.addEventListener('click', () => this.createNewConversation());
        this.toggleSidebar.addEventListener('click', () => this.toggleSidebarVisibility());
        this.toggleSidebarCollapsedBtn.addEventListener('click', () => this.toggleSidebarVisibility());
        this.mobileMenuBtn.addEventListener('click', () => this.toggleSidebarVisibility());
        this.sidebarOverlay.addEventListener('click', () => this.toggleSidebarVisibility());
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });

        // Send on Ctrl+Enter
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.handleSubmit(e);
            }
        });

        // Settings
        this.appSettings.addEventListener('click', () => this.openSettings());
        this.closeSettings.addEventListener('click', () => this.closeSettingsModal());
        this.settingsModal.querySelector('.settings-modal-overlay').addEventListener('click', () => this.closeSettingsModal());
        this.themeSelect.addEventListener('change', () => this.previewTheme());
        this.saveSettings.addEventListener('click', () => this.saveSettingsChanges());
        this.resetSettings.addEventListener('click', () => this.resetSettingsToDefaults());
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.settingsModal.classList.contains('active')) {
                this.closeSettingsModal();
            }
        });
    }

    initializeSidebarState() {
        // Initialize sidebar button states
        const isCollapsed = this.sidebar.classList.contains('collapsed');
        this.toggleSidebar.textContent = isCollapsed ? '›' : '‹';
        
        // Mobile button always shows hamburger initially
        this.mobileMenuBtn.textContent = '☰';
    }

    // ==== CONNECTION AND MODELS ====
    async checkConnection() {
        try {
            const response = await fetch(`${this.baseUrl}/tags`);
            if (response.ok) {
                this.statusIndicator.classList.add('connected');
                this.statusIndicator.title = 'Connected to Ollama';
                console.log('Connection check: OK');
            }
        } catch (error) {
            this.statusIndicator.classList.remove('connected');
            this.statusIndicator.title = 'Disconnected from Ollama';
            this.showError('Cannot connect to Ollama through Flask proxy');
            console.error('Connection check failed:', error);
        }
    }

    async loadModels() {
        try {
            console.log('Loading models...');
            const response = await fetch(`${this.baseUrl}/tags`);
            if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to fetch models`);
            
            const data = await response.json();
            console.log('Models loaded:', data);
            this.populateModelSelect(data.models || []);
            this.statusIndicator.classList.add('connected');
        } catch (error) {
            console.error('Error loading models:', error);
            this.statusIndicator.classList.remove('connected');
            this.showError(`Failed to load models: ${error.message}`);
        }
    }

    populateModelSelect(models) {
        this.modelSelect.innerHTML = '<option value="">Select a model...</option>';
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = `${model.name} (${this.formatSize(model.size)})`;
            this.modelSelect.appendChild(option);
        });
        console.log(`Populated ${models.length} models`);
    }

    formatSize(bytes) {
        const sizes = ['B', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 B';
        const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    // ==== FILE UPLOAD FUNCTIONALITY ====
    triggerFileInput() {
        this.fileInput.click();
    }

    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        files.forEach(file => this.uploadFile(file));
        
        // Clear the input so the same file can be selected again
        event.target.value = '';
    }

    handleDragOver(event) {
        event.preventDefault();
        event.stopPropagation();
        this.chatMessages.classList.add('drag-over');
    }

    handleDragLeave(event) {
        event.preventDefault();
        event.stopPropagation();
        this.chatMessages.classList.remove('drag-over');
    }

    handleDrop(event) {
        event.preventDefault();
        event.stopPropagation();
        this.chatMessages.classList.remove('drag-over');
        
        const files = Array.from(event.dataTransfer.files);
        files.forEach(file => this.uploadFile(file));
    }

    async uploadFile(file) {
        console.log('Uploading file:', file.name, file.size, file.type);
        
        // Validate file
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            return;
        }
        
        // Create attachment preview immediately
        const attachmentId = this.generateTempId();
        const attachmentData = {
            id: attachmentId,
            original_filename: file.name,
            file_size: file.size,
            file_size_str: this.formatFileSize(file.size),
            mime_type: file.type,
            uploading: true
        };
        
        this.pendingAttachments.push(attachmentData);
        this.renderAttachments();
        
        try {
            // Create FormData for file upload
            const formData = new FormData();
            formData.append('file', file);
            
            // Upload file
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Upload failed');
            }
            
            const result = await response.json();
            console.log('Upload successful:', result);
            
            // Update attachment data with server response - MAKE SURE file_path is included
            const attachment = this.pendingAttachments.find(a => a.id === attachmentId);
            if (attachment) {
                Object.assign(attachment, {
                    filename: result.filename,
                    file_path: result.file_path,  // This is crucial for image processing
                    has_text: result.has_text,
                    text_preview: result.text_preview,
                    extracted_text: result.extracted_text,
                    uploading: false,
                    uploaded: true
                });
            }
            
            this.renderAttachments();
            
        } catch (error) {
            console.error('Upload error:', error);
            
            // Mark attachment as failed
            const attachment = this.pendingAttachments.find(a => a.id === attachmentId);
            if (attachment) {
                attachment.uploading = false;
                attachment.error = error.message;
            }
            
            this.renderAttachments();
            this.showError(`Failed to upload ${file.name}: ${error.message}`);
        }
    }

    validateFile(file) {
        if (!file) {
            return { valid: false, error: 'No file selected' };
        }
        
        if (file.size > this.maxFileSize) {
            return { 
                valid: false, 
                error: `File too large. Maximum size is ${this.formatFileSize(this.maxFileSize)}` 
            };
        }
        
        if (!this.allowedTypes.includes(file.type)) {
            return { 
                valid: false, 
                error: `File type not supported: ${file.type}` 
            };
        }
        
        return { valid: true };
    }

    renderAttachments() {
        if (this.pendingAttachments.length === 0) {
            this.attachmentsPreview.style.display = 'none';
            this.attachFileBtn.classList.remove('has-files');
            return;
        }
        
        this.attachmentsPreview.style.display = 'block';
        this.attachFileBtn.classList.add('has-files');
        
        this.attachmentsList.innerHTML = '';
        
        this.pendingAttachments.forEach(attachment => {
            const item = this.createAttachmentItem(attachment);
            this.attachmentsList.appendChild(item);
        });
    }

    createAttachmentItem(attachment) {
        const item = document.createElement('div');
        item.className = 'attachment-item';
        
        if (attachment.uploading) {
            item.classList.add('uploading');
        }
        if (attachment.error) {
            item.classList.add('error');
        }
        
        const icon = this.getFileIcon(attachment.mime_type);
        const status = attachment.uploading ? 'Uploading...' : 
                    attachment.error ? `Error: ${attachment.error}` :
                    attachment.has_text ? 'Text extracted' : 'File ready';
        
        item.innerHTML = `
            <div class="attachment-icon ${icon.class}">${icon.text}</div>
            <div class="attachment-info">
                <div class="attachment-name" title="${attachment.original_filename}">
                    ${attachment.original_filename}
                </div>
                <div class="attachment-meta">
                    ${attachment.file_size_str} • ${status}
                </div>
            </div>
            <div class="attachment-actions">
                ${!attachment.uploading ? `
                    <button class="attachment-action remove" data-id="${attachment.id}" title="Remove">✕</button>
                ` : ''}
            </div>
        `;
        
        // Add remove functionality
        const removeBtn = item.querySelector('.remove');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => this.removeAttachment(attachment.id));
        }
        
        return item;
    }

    getFileIcon(mimeType) {
        if (mimeType.startsWith('image/')) {
            return { class: 'img', text: 'IMG' };
        } else if (mimeType === 'application/pdf') {
            return { class: 'pdf', text: 'PDF' };
        } else if (mimeType.includes('word') || mimeType.includes('document')) {
            return { class: 'doc', text: 'DOC' };
        } else if (mimeType === 'text/plain' || mimeType === 'text/markdown') {
            return { class: 'txt', text: 'TXT' };
        } else if (mimeType === 'text/csv' || mimeType.includes('spreadsheet')) {
            return { class: 'csv', text: 'CSV' };
        } else if (mimeType === 'application/json') {
            return { class: 'json', text: 'JSON' };
        } else {
            return { class: 'other', text: 'FILE' };
        }
    }

    removeAttachment(attachmentId) {
        this.pendingAttachments = this.pendingAttachments.filter(a => a.id !== attachmentId);
        this.renderAttachments();
        console.log('Removed attachment:', attachmentId);
    }

    clearAllAttachments() {
        if (this.pendingAttachments.length > 0 && 
            confirm('Remove all attached files?')) {
            this.pendingAttachments = [];
            this.renderAttachments();
            console.log('Cleared all attachments');
        }
    }

    generateTempId() {
        return 'temp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // ==== CONVERSATION MANAGEMENT ====
    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            if (!response.ok) throw new Error('Failed to load conversations');
            
            this.conversations = await response.json();
            this.renderConversations();
            console.log(`Loaded ${this.conversations.length} conversations`);
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.showError('Failed to load conversations');
        }
    }

    renderConversations() {
        this.conversationsList.innerHTML = '';
        
        if (this.conversations.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'empty-conversations';
            emptyDiv.innerHTML = '<p>No conversations yet.<br>Start by creating a new one!</p>';
            emptyDiv.style.cssText = 'text-align: center; padding: 20px; color: #666; font-style: italic;';
            this.conversationsList.appendChild(emptyDiv);
            return;
        }
        
        this.conversations.forEach(conversation => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            if (conversation.id === this.currentConversationId) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <div class="conversation-title">${conversation.title}</div>
                <div class="conversation-meta">
                    <span>${conversation.model_name}</span>
                    <span>${new Date(conversation.updated_at).toLocaleDateString()}</span>
                </div>
                <div class="conversation-actions">
                    <button class="action-btn delete-btn" data-id="${conversation.id}" title="Delete">🗑</button>
                </div>
            `;
            
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('action-btn')) {
                    this.loadConversation(conversation.id);
                }
            });
            
            // Delete button
            const deleteBtn = item.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm('Are you sure you want to delete this conversation?')) {
                    this.deleteConversation(conversation.id);
                }
            });
            
            this.conversationsList.appendChild(item);
        });
    }

    async createNewConversation() {
        if (!this.currentModel) {
            alert('Please select a model first');
            return;
        }
        
        try {
            const response = await fetch('/api/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: 'New Conversation',
                    model_name: this.currentModel
                })
            });
            
            if (!response.ok) throw new Error('Failed to create conversation');
            
            const newConversation = await response.json();
            this.conversations.unshift(newConversation);
            this.renderConversations();
            
            // Switch to new conversation
            this.currentConversationId = newConversation.id;
            this.conversationHistory = [];
            this.clearMessages();
            this.addMessage('assistant', `Started new conversation with ${this.currentModel}. How can I help you?`);
            
            console.log('Created new conversation:', newConversation.id);
        } catch (error) {
            console.error('Error creating conversation:', error);
            this.showError('Failed to create new conversation');
        }
    }

    async loadConversation(conversationId) {
        try {
            console.log(`Loading conversation ${conversationId}...`);
            const response = await fetch(`/api/conversations/${conversationId}`);
            if (!response.ok) throw new Error('Failed to load conversation');
            
            const conversation = await response.json();
            console.log('Loaded conversation data:', conversation);
            
            // Update current state
            this.currentConversationId = conversationId;
            this.currentModel = conversation.model_name;
            this.modelSelect.value = conversation.model_name;
            this.sendButton.disabled = false;
            
            // Load conversation history
            this.conversationHistory = conversation.messages || [];
            console.log(`Conversation history has ${this.conversationHistory.length} messages:`, this.conversationHistory);
            
            // Clear and render messages
            this.clearMessages();
            if (this.conversationHistory.length > 0) {
                this.conversationHistory.forEach((message, index) => {
                    console.log(`Rendering message ${index + 1}:`, message.role, message.content.substring(0, 50) + '...');
                    this.addMessage(message.role, message.content);
                });
            } else {
                this.addMessage('assistant', `Loaded conversation with ${this.currentModel}. No previous messages found.`);
            }
            
            // Update active conversation in sidebar
            this.renderConversations();
            
            console.log(`Successfully loaded conversation ${conversationId} with ${this.conversationHistory.length} messages`);
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showError('Failed to load conversation');
        }
    }

    async deleteConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) throw new Error('Failed to delete conversation');
            
            // Remove from local array
            this.conversations = this.conversations.filter(c => c.id !== conversationId);
            this.renderConversations();
            
            // If this was the current conversation, clear it
            if (this.currentConversationId === conversationId) {
                this.currentConversationId = null;
                this.conversationHistory = [];
                this.clearMessages();
                this.addMessage('assistant', 'Conversation deleted. Create a new one to continue chatting.');
            }
            
            console.log(`Deleted conversation ${conversationId}`);
        } catch (error) {
            console.error('Error deleting conversation:', error);
            this.showError('Failed to delete conversation');
        }
    }

    // ==== CHAT FUNCTIONALITY ====
    handleModelChange(e) {
        this.currentModel = e.target.value;
        this.sendButton.disabled = !this.currentModel;
        console.log('Selected model:', this.currentModel);
        
        if (this.currentModel && !this.currentConversationId) {
            this.clearMessages();
            this.addMessage('assistant', `Model selected: ${this.currentModel}. Create a new conversation to start chatting!`);
        }
    }

    handleSubmit(e) {
        e.preventDefault();
        if (!this.messageInput.value.trim() || !this.currentModel) return;
        
        const message = this.messageInput.value.trim();
        
        // DON'T clear the input here - let sendMessage handle it
        // DON'T call addMessage here - let sendMessage handle it
        
        if (!this.currentConversationId) {
            // Auto-create conversation if none exists
            this.createNewConversation().then(() => {
                if (this.currentConversationId) {
                    console.log('Auto-created conversation, now sending message:', message);
                    this.sendMessage(message); // Only call sendMessage
                }
            });
        } else {
            console.log('Sending message:', message);
            this.sendMessage(message); // Only call sendMessage
        }
    }

    async sendMessage(message) {
        this.showTyping(true);
        this.sendButton.disabled = true;
        console.log('Starting sendMessage with attachments:', this.pendingAttachments.length);

        try {
            // Get uploaded attachments (filter out failed uploads)
            const validAttachments = this.pendingAttachments.filter(a => a.uploaded && !a.error);
            console.log('Valid attachments to send:', validAttachments);

            // Clear the input and attachments UI immediately
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto'; // Reset textarea height
            
            // Create a copy of attachments before clearing
            const attachmentsCopy = validAttachments.map(a => ({
                original_filename: a.original_filename,
                file_size: a.file_size,
                file_size_str: a.file_size_str,
                mime_type: a.mime_type,
                file_path: a.file_path
            }));

            // Clear pending attachments UI
            this.pendingAttachments = [];
            this.renderAttachments();

            // Add user message to UI immediately for fast feedback
            this.addMessage('user', message, attachmentsCopy);

            // Send to API
            const response = await fetch(`${this.baseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: this.currentModel,
                    message: message,
                    history: this.conversationHistory, // Send current history
                    conversation_id: this.currentConversationId,
                    attachments: validAttachments
                })
            });

            console.log('Chat response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Response error:', errorText);
                throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
            }

            // Add to conversation history after successful API call
            this.conversationHistory.push({ 
                role: 'user', 
                content: message,
                attachments: attachmentsCopy
            });

            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = '';
            let messageElement = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n').filter(line => line.trim());

                for (const line of lines) {
                    try {
                        const data = JSON.parse(line);
                        
                        if (data.content) {
                            assistantMessage += data.content;
                            
                            if (!messageElement) {
                                messageElement = this.addMessage('assistant', '');
                            }
                            
                            const contentElement = messageElement.querySelector('.message-content');
                            if (this.markdownEnabled !== false) {
                                contentElement.innerHTML = marked.parse(assistantMessage);
                            } else {
                                contentElement.textContent = assistantMessage;
                            }
                            
                            this.scrollToBottom();
                        }
                    } catch (e) {
                        console.log('Failed to parse line as JSON:', line, e);
                    }
                }
            }

            if (assistantMessage) {
                this.conversationHistory.push({ role: 'assistant', content: assistantMessage });
                this.loadConversations(); // Update sidebar
            } else {
                this.showError('No response received from the model. Try again.');
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.showError(`Error: ${error.message}`);
            
            // Clear UI on error
            this.pendingAttachments = [];
            this.renderAttachments();
        } finally {
            this.showTyping(false);
            this.sendButton.disabled = !this.currentModel;
        }
    }

    // ==== UI HELPER METHODS ====
    addMessage(role, content, attachments = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        // Render content based on role and settings
        let renderedContent;
        if (role === 'assistant' && content && this.markdownEnabled !== false) {
            // Assistant messages: render markdown
            renderedContent = marked.parse(content);
        } else {
            // User messages: escape HTML to show it as text
            renderedContent = this.escapeHtml(content);
        }
        
        // Add attachment info for user messages
        let attachmentHtml = '';
        if (role === 'user' && attachments && attachments.length > 0) {
            attachmentHtml = '<div class="message-attachments">';
            attachments.forEach(att => {
                const icon = this.getFileIcon(att.mime_type);
                attachmentHtml += `
                    <div class="message-attachment">
                        <span class="attachment-icon ${icon.class}">${icon.text}</span>
                        <span class="attachment-name">${att.original_filename}</span>
                    </div>
                `;
            });
            attachmentHtml += '</div>';
        }
        
        messageDiv.innerHTML = `
            <div class="message-content">${renderedContent}</div>
            ${attachmentHtml}
        `;
        
        this.chatMessages.appendChild(messageDiv);
        
        if (this.autoScrollEnabled !== false) {
            this.scrollToBottom();
        }
        
        console.log(`Added ${role} message:`, content);
        return messageDiv;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showTyping(show) {
        this.typingIndicator.style.display = show ? 'flex' : 'none';
        if (show) this.scrollToBottom();
        console.log('Typing indicator:', show ? 'shown' : 'hidden');
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        this.chatMessages.appendChild(errorDiv);
        this.scrollToBottom();
        console.log('Error message:', message);
    }

    clearMessages() {
        const messages = this.chatMessages.querySelectorAll('.message:not(:first-child), .error-message');
        messages.forEach(msg => msg.remove());
        console.log('Cleared messages');
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 10);
    }

    toggleSidebarVisibility() {
        this.sidebar.classList.toggle('collapsed');
        
        // Update the regular toggle button
        const isCollapsed = this.sidebar.classList.contains('collapsed');
        this.toggleSidebar.textContent = isCollapsed ? '›' : '‹';
        
        // Update mobile button icon
        this.mobileMenuBtn.textContent = isCollapsed ? '☰' : '✕';
    }

    // ==== SETTINGS FUNCTIONALITY ====
    async openSettings() {
        try {
            // Load current settings
            const response = await fetch('/api/settings/theme');
            if (response.ok) {
                const data = await response.json();
                this.themeSelect.value = data.current_theme;
                this.previewTheme();
            }
            
            // Load other settings from localStorage or defaults
            this.markdownEnabled.checked = localStorage.getItem('markdownEnabled') !== 'false';
            this.autoScrollEnabled.checked = localStorage.getItem('autoScrollEnabled') !== 'false';
            
            this.settingsModal.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        } catch (error) {
            console.error('Error opening settings:', error);
            this.showError('Failed to load settings');
        }
    }

    closeSettingsModal() {
        this.settingsModal.classList.remove('active');
        document.body.style.overflow = ''; // Restore scrolling
    }

    previewTheme() {
        const selectedTheme = this.themeSelect.value;
        // You could add a preview by temporarily applying theme colors to the preview element
        // For now, the preview uses the CSS variables which will update on save
        console.log('Previewing theme:', selectedTheme);
    }

    async saveSettingsChanges() {
        try {
            // Save theme
            const themeResponse = await fetch('/api/settings/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    theme: this.themeSelect.value
                })
            });
            
            if (!themeResponse.ok) {
                throw new Error('Failed to save theme');
            }
            
            // Save other settings to localStorage
            localStorage.setItem('markdownEnabled', this.markdownEnabled.checked);
            localStorage.setItem('autoScrollEnabled', this.autoScrollEnabled.checked);
            
            // Apply settings immediately
            this.applySettings();
            
            // Reload page to apply theme changes
            window.location.reload();
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showError('Failed to save settings');
        }
    }

    async resetSettingsToDefaults() {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            try {
                // Reset theme to default
                const response = await fetch('/api/settings/theme', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        theme: 'zebra'
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to reset theme');
                }
                
                // Clear localStorage
                localStorage.removeItem('markdownEnabled');
                localStorage.removeItem('autoScrollEnabled');
                
                // Reload page to apply changes
                window.location.reload();
                
            } catch (error) {
                console.error('Error resetting settings:', error);
                this.showError('Failed to reset settings');
            }
        }
    }

    applySettings() {
        // Apply markdown setting
        this.markdownEnabled = localStorage.getItem('markdownEnabled') !== 'false';
        
        // Apply auto-scroll setting
        this.autoScrollEnabled = localStorage.getItem('autoScrollEnabled') !== 'false';
        
        console.log('Applied settings:', {
            markdown: this.markdownEnabled,
            autoScroll: this.autoScrollEnabled
        });
    }
}

// Initialize the chat when the page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing OllamaChat...');
    new OllamaChat();
});