/**
 * MakeMyRecipe Chat Application
 * A responsive chat interface for recipe assistance with WebSocket support
 */

class MakeMyRecipeApp {
    constructor() {
        this.ws = null;
        this.currentConversationId = null;
        this.userId = this.generateUserId();
        this.conversations = new Map();
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;

        this.initializeElements();
        this.bindEvents();
        this.loadConversations();
        this.connect();
    }

    /**
     * Initialize DOM elements
     */
    initializeElements() {
        // Main elements
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.connectionStatus = document.getElementById('connectionStatus');
        this.characterCount = document.getElementById('characterCount');

        // Sidebar elements
        this.sidebar = document.getElementById('sidebar');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.conversationList = document.getElementById('conversationList');
        this.conversationSearch = document.getElementById('conversationSearch');

        // Modal elements
        this.errorModal = document.getElementById('errorModal');
        this.errorMessage = document.getElementById('errorMessage');
        this.errorModalClose = document.getElementById('errorModalClose');
        this.errorModalOk = document.getElementById('errorModalOk');
        this.loadingOverlay = document.getElementById('loadingOverlay');
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Message input events
        this.messageInput.addEventListener('input', this.handleInputChange.bind(this));
        this.messageInput.addEventListener('keydown', this.handleKeyDown.bind(this));
        this.sendButton.addEventListener('click', this.sendMessage.bind(this));

        // Sidebar events
        this.newChatBtn.addEventListener('click', this.startNewConversation.bind(this));
        this.sidebarToggle.addEventListener('click', this.toggleSidebar.bind(this));
        this.mobileSidebarToggle.addEventListener('click', this.toggleSidebar.bind(this));
        this.conversationSearch.addEventListener('input', this.handleConversationSearch.bind(this));

        // Modal events
        this.errorModalClose.addEventListener('click', this.hideErrorModal.bind(this));
        this.errorModalOk.addEventListener('click', this.hideErrorModal.bind(this));

        // Window events
        window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
        window.addEventListener('resize', this.handleResize.bind(this));

        // Click outside sidebar to close on mobile
        document.addEventListener('click', this.handleDocumentClick.bind(this));
    }

    /**
     * Generate a unique user ID
     */
    generateUserId() {
        let userId = localStorage.getItem('makemyrecipe_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('makemyrecipe_user_id', userId);
        }
        return userId;
    }

    /**
     * Connect to WebSocket
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }

        this.updateConnectionStatus('connecting');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.userId}`;

        try {
            this.ws = new WebSocket(wsUrl);
            this.ws.onopen = this.handleWebSocketOpen.bind(this);
            this.ws.onmessage = this.handleWebSocketMessage.bind(this);
            this.ws.onclose = this.handleWebSocketClose.bind(this);
            this.ws.onerror = this.handleWebSocketError.bind(this);
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleConnectionError();
        }
    }

    /**
     * Handle WebSocket open event
     */
    handleWebSocketOpen() {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.updateConnectionStatus('connected');
    }

    /**
     * Handle WebSocket message event
     */
    handleWebSocketMessage(event) {
        try {
            const message = JSON.parse(event.data);
            this.handleIncomingMessage(message);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    /**
     * Handle WebSocket close event
     */
    handleWebSocketClose(event) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnected = false;
        this.updateConnectionStatus('disconnected');

        // Attempt to reconnect if not a clean close
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
        }
    }

    /**
     * Handle WebSocket error event
     */
    handleWebSocketError(error) {
        console.error('WebSocket error:', error);
        this.handleConnectionError();
    }

    /**
     * Attempt to reconnect to WebSocket
     */
    attemptReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);

        setTimeout(() => {
            if (!this.isConnected) {
                this.connect();
            }
        }, delay);
    }

    /**
     * Handle connection errors
     */
    handleConnectionError() {
        this.isConnected = false;
        this.updateConnectionStatus('disconnected');
        this.showError('Connection failed. Please check your internet connection and try again.');
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(status) {
        this.connectionStatus.className = `connection-status ${status}`;

        const statusText = {
            connecting: 'Connecting...',
            connected: 'Connected',
            disconnected: 'Disconnected'
        };

        const statusIcon = {
            connecting: 'fas fa-circle',
            connected: 'fas fa-circle',
            disconnected: 'fas fa-circle'
        };

        this.connectionStatus.querySelector('i').className = statusIcon[status];
        this.connectionStatus.querySelector('span').textContent = statusText[status];
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleIncomingMessage(message) {
        switch (message.type) {
            case 'status':
                console.log('Status message:', message.data);
                break;

            case 'user_message':
                // User message confirmation - already displayed
                break;

            case 'assistant_message':
                this.hideTypingIndicator();
                this.displayMessage('assistant', message.data.message, message.data.citations);
                this.currentConversationId = message.data.conversation_id;
                this.updateConversationInSidebar(message.data.conversation_id);
                break;

            case 'error':
                this.hideTypingIndicator();
                this.showError(message.data.error);
                break;

            case 'pong':
                // Heartbeat response
                break;

            default:
                console.log('Unknown message type:', message.type);
        }
    }

    /**
     * Send a message
     */
    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.isConnected) {
            return;
        }

        // Display user message immediately
        this.displayMessage('user', message);

        // Clear input
        this.messageInput.value = '';
        this.updateCharacterCount();
        this.updateSendButton();

        // Show typing indicator
        this.showTypingIndicator();

        // Send via WebSocket
        const wsMessage = {
            type: 'chat',
            message: message,
            conversation_id: this.currentConversationId
        };

        try {
            this.ws.send(JSON.stringify(wsMessage));
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.showError('Failed to send message. Please try again.');
        }
    }

    /**
     * Display a message in the chat
     */
    displayMessage(role, content, citations = []) {
        // Remove welcome message if it exists
        const welcomeMessage = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        const messageElement = document.createElement('div');
        messageElement.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';

        const messageText = document.createElement('div');
        messageText.className = 'message-text';

        // Process message content for recipes and formatting
        if (role === 'assistant') {
            messageText.innerHTML = this.processMessageContent(content);

            // Add citations if present
            if (citations && citations.length > 0) {
                const citationsElement = this.createCitationsElement(citations);
                messageBubble.appendChild(citationsElement);
            }
        } else {
            messageText.textContent = content;
        }

        messageBubble.appendChild(messageText);

        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();

        messageContent.appendChild(messageBubble);
        messageContent.appendChild(timestamp);

        messageElement.appendChild(avatar);
        messageElement.appendChild(messageContent);

        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    /**
     * Process message content for formatting and recipe cards
     */
    processMessageContent(content) {
        // Convert markdown-like formatting to HTML
        let processed = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        // Wrap in paragraphs
        processed = '<p>' + processed + '</p>';

        // Clean up empty paragraphs
        processed = processed.replace(/<p><\/p>/g, '');

        return processed;
    }

    /**
     * Create citations element
     */
    createCitationsElement(citations) {
        const citationsContainer = document.createElement('div');
        citationsContainer.className = 'citations';

        const title = document.createElement('div');
        title.className = 'citations-title';
        title.innerHTML = '<i class="fas fa-link"></i> Sources';
        citationsContainer.appendChild(title);

        citations.forEach(citation => {
            const citationElement = document.createElement('a');
            citationElement.className = 'citation';
            citationElement.href = citation.url;
            citationElement.target = '_blank';
            citationElement.rel = 'noopener noreferrer';

            const citationTitle = document.createElement('div');
            citationTitle.className = 'citation-title';
            citationTitle.textContent = citation.title;

            const citationSnippet = document.createElement('div');
            citationSnippet.className = 'citation-snippet';
            citationSnippet.textContent = citation.snippet || '';

            const citationUrl = document.createElement('div');
            citationUrl.className = 'citation-url';
            citationUrl.textContent = citation.url;

            citationElement.appendChild(citationTitle);
            if (citation.snippet) {
                citationElement.appendChild(citationSnippet);
            }
            citationElement.appendChild(citationUrl);

            citationsContainer.appendChild(citationElement);
        });

        return citationsContainer;
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        this.typingIndicator.style.display = 'flex';
        this.scrollToBottom();
    }

    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    /**
     * Handle input change
     */
    handleInputChange() {
        this.updateCharacterCount();
        this.updateSendButton();
        this.autoResizeTextarea();
    }

    /**
     * Handle key down events
     */
    handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    /**
     * Update character count
     */
    updateCharacterCount() {
        const length = this.messageInput.value.length;
        const maxLength = 2000;

        this.characterCount.textContent = `${length}/${maxLength}`;

        if (length > maxLength * 0.9) {
            this.characterCount.className = 'character-count error';
        } else if (length > maxLength * 0.8) {
            this.characterCount.className = 'character-count warning';
        } else {
            this.characterCount.className = 'character-count';
        }
    }

    /**
     * Update send button state
     */
    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || !this.isConnected;
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    /**
     * Start a new conversation
     */
    startNewConversation() {
        this.currentConversationId = null;
        this.clearMessages();
        this.showWelcomeMessage();
        this.updateActiveConversation(null);
    }

    /**
     * Clear all messages
     */
    clearMessages() {
        this.messagesContainer.innerHTML = '';
    }

    /**
     * Show welcome message
     */
    showWelcomeMessage() {
        const welcomeHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-chef-hat"></i>
                </div>
                <h2>Welcome to MakeMyRecipe!</h2>
                <p>I'm your AI cooking assistant. I can help you:</p>
                <ul>
                    <li><i class="fas fa-search"></i> Find recipes based on ingredients you have</li>
                    <li><i class="fas fa-heart"></i> Suggest dishes for your dietary preferences</li>
                    <li><i class="fas fa-globe"></i> Explore cuisines from around the world</li>
                    <li><i class="fas fa-clock"></i> Get quick meal ideas for busy days</li>
                </ul>
                <p>Just type your question below to get started!</p>
            </div>
        `;
        this.messagesContainer.innerHTML = welcomeHTML;
    }

    /**
     * Toggle sidebar
     */
    toggleSidebar() {
        this.sidebar.classList.toggle('open');
    }

    /**
     * Handle document click for mobile sidebar
     */
    handleDocumentClick(event) {
        if (window.innerWidth <= 768) {
            const isClickInsideSidebar = this.sidebar.contains(event.target);
            const isClickOnToggle = this.mobileSidebarToggle.contains(event.target);

            if (!isClickInsideSidebar && !isClickOnToggle && this.sidebar.classList.contains('open')) {
                this.sidebar.classList.remove('open');
            }
        }
    }

    /**
     * Handle window resize
     */
    handleResize() {
        if (window.innerWidth > 768) {
            this.sidebar.classList.remove('open');
        }
    }

    /**
     * Load conversations from API
     */
    async loadConversations() {
        try {
            const response = await fetch(`/api/conversations?user_id=${this.userId}&limit=50`);
            if (response.ok) {
                const data = await response.json();
                this.displayConversations(data.conversations);
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
        }
    }

    /**
     * Display conversations in sidebar
     */
    displayConversations(conversations) {
        this.conversationList.innerHTML = '';

        if (conversations.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-state';
            emptyState.innerHTML = `
                <p style="text-align: center; color: var(--text-muted); padding: var(--spacing-lg);">
                    <i class="fas fa-comments" style="font-size: 2rem; margin-bottom: var(--spacing-md); display: block;"></i>
                    No conversations yet.<br>Start a new chat to begin!
                </p>
            `;
            this.conversationList.appendChild(emptyState);
            return;
        }

        conversations.forEach(conversation => {
            this.conversations.set(conversation.conversation_id, conversation);
            const conversationElement = this.createConversationElement(conversation);
            this.conversationList.appendChild(conversationElement);
        });
    }

    /**
     * Create conversation element
     */
    createConversationElement(conversation) {
        const element = document.createElement('div');
        element.className = 'conversation-item';
        element.dataset.conversationId = conversation.conversation_id;

        const title = conversation.metadata?.title || this.generateConversationTitle(conversation);
        const preview = this.getConversationPreview(conversation);
        const date = new Date(conversation.updated_at).toLocaleDateString();

        element.innerHTML = `
            <div class="conversation-title">${title}</div>
            <div class="conversation-preview">${preview}</div>
            <div class="conversation-date">${date}</div>
        `;

        element.addEventListener('click', () => {
            this.loadConversation(conversation.conversation_id);
        });

        return element;
    }

    /**
     * Generate conversation title from first message
     */
    generateConversationTitle(conversation) {
        const firstUserMessage = conversation.messages.find(msg => msg.role === 'user');
        if (firstUserMessage) {
            return firstUserMessage.content.substring(0, 50) + (firstUserMessage.content.length > 50 ? '...' : '');
        }
        return 'New Conversation';
    }

    /**
     * Get conversation preview from last message
     */
    getConversationPreview(conversation) {
        const lastMessage = conversation.messages[conversation.messages.length - 1];
        if (lastMessage) {
            const content = lastMessage.content.substring(0, 100);
            return content + (lastMessage.content.length > 100 ? '...' : '');
        }
        return 'No messages';
    }

    /**
     * Load a specific conversation
     */
    async loadConversation(conversationId) {
        try {
            this.showLoading();

            const response = await fetch(`/api/conversations/${conversationId}`);
            if (response.ok) {
                const conversation = await response.json();
                this.displayConversation(conversation);
                this.currentConversationId = conversationId;
                this.updateActiveConversation(conversationId);
            } else {
                this.showError('Failed to load conversation');
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showError('Failed to load conversation');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Display a loaded conversation
     */
    displayConversation(conversation) {
        this.clearMessages();

        conversation.messages.forEach(message => {
            if (message.role !== 'system') {
                this.displayMessage(message.role, message.content);
            }
        });

        this.scrollToBottom();
    }

    /**
     * Update active conversation in sidebar
     */
    updateActiveConversation(conversationId) {
        // Remove active class from all conversations
        this.conversationList.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to current conversation
        if (conversationId) {
            const activeItem = this.conversationList.querySelector(`[data-conversation-id="${conversationId}"]`);
            if (activeItem) {
                activeItem.classList.add('active');
            }
        }
    }

    /**
     * Update conversation in sidebar after new message
     */
    updateConversationInSidebar(conversationId) {
        // Reload conversations to get updated data
        this.loadConversations();
    }

    /**
     * Handle conversation search
     */
    handleConversationSearch() {
        const query = this.conversationSearch.value.toLowerCase();
        const conversationItems = this.conversationList.querySelectorAll('.conversation-item');

        conversationItems.forEach(item => {
            const title = item.querySelector('.conversation-title').textContent.toLowerCase();
            const preview = item.querySelector('.conversation-preview').textContent.toLowerCase();

            if (title.includes(query) || preview.includes(query)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }

    /**
     * Show error modal
     */
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorModal.style.display = 'flex';
    }

    /**
     * Hide error modal
     */
    hideErrorModal() {
        this.errorModal.style.display = 'none';
    }

    /**
     * Show loading overlay
     */
    showLoading() {
        this.loadingOverlay.style.display = 'flex';
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }

    /**
     * Handle before unload
     */
    handleBeforeUnload() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.close(1000, 'Page unload');
        }
    }

    /**
     * Send heartbeat to keep connection alive
     */
    sendHeartbeat() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
        }
    }

    /**
     * Start heartbeat interval
     */
    startHeartbeat() {
        setInterval(() => {
            this.sendHeartbeat();
        }, 30000); // Send heartbeat every 30 seconds
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MakeMyRecipeApp();
    window.app.startHeartbeat();
});

// Handle service worker registration for PWA support (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Service worker registration can be added here for PWA support
    });
}
