class ArtifactManager {
    constructor() {
        this.artifacts = new Map(); // identifier -> artifact data
        this.currentArtifactId = null;
        this.artifactPane = null;
        this.initializePane();
    }
    
    initializePane() {
        // Create artifact pane structure
        const pane = document.createElement('div');
        pane.id = 'artifact-pane';
        pane.className = 'artifact-pane hidden';
        pane.innerHTML = `
            <div class="artifact-header">
                <button class="artifact-nav prev">←</button>
                <span class="artifact-title"></span>
                <button class="artifact-nav next">→</button>
                <button class="artifact-close">✕</button>
            </div>
            <div class="artifact-content"></div>
            <div class="artifact-footer">
                <button class="artifact-copy">Copy</button>
            </div>
        `;
        document.body.appendChild(pane);
        this.artifactPane = pane;
        this.setupEventListeners();
    }
    
    addArtifact(identifier, metadata, content) {
        this.artifacts.set(identifier, {
            metadata,
            content,
            timestamp: Date.now()
        });
    }
    
    showArtifact(identifier) {
        const artifact = this.artifacts.get(identifier);
        if (!artifact) return;
        
        this.currentArtifactId = identifier;
        this.artifactPane.classList.remove('hidden');
        this.renderArtifact(artifact);
    }
    
    renderArtifact(artifact) {
        const contentDiv = this.artifactPane.querySelector('.artifact-content');
        const titleSpan = this.artifactPane.querySelector('.artifact-title');
        
        titleSpan.textContent = artifact.metadata.title;
        
        if (artifact.metadata.artifact_type === 'code') {
            // Use your existing CodeBlock component
            contentDiv.innerHTML = `<pre><code class="language-${artifact.metadata.language}">${artifact.content}</code></pre>`;
            // Apply syntax highlighting
        } else {
            // Use your existing MarkdownText component
            contentDiv.innerHTML = marked.parse(artifact.content);
        }
    }
    
    hidePane() {
        this.artifactPane.classList.add('hidden');
    }
    
    navigateArtifacts(direction) {
        // Implement prev/next navigation
    }
}

// Global instance
window.artifactManager = new ArtifactManager();