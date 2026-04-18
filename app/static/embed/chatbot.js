/**
 * GraphRAG Embeddable Chatbot Widget
 * Standalone JavaScript chatbot that can be embedded in any website
 */

(function() {
  'use strict';
  
  // Widget state
  const state = {
    config: null,
    isOpen: false,
    messages: [],
    isLoading: false
  };
  
  // Create widget HTML
  function createWidget() {
    const container = document.createElement('div');
    container.id = 'graphrag-chatbot';
    container.className = 'graphrag-chatbot-container';
    
    container.innerHTML = `
      <div class="graphrag-chat-button" id="graphrag-chat-toggle">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      
      <div class="graphrag-chat-window" id="graphrag-chat-window" style="display: none;">
        <div class="graphrag-chat-header">
          <h3 id="graphrag-chat-title">AI Assistant</h3>
          <button class="graphrag-close-btn" id="graphrag-close-btn">×</button>
        </div>
        
        <div class="graphrag-chat-messages" id="graphrag-chat-messages">
          <div class="graphrag-message graphrag-bot-message">
            <p id="graphrag-greeting">Hello! How can I help you today?</p>
          </div>
        </div>
        
        <div class="graphrag-chat-input-container">
          <input 
            type="text" 
            id="graphrag-chat-input" 
            placeholder="Ask a question..."
            autocomplete="off"
          />
          <button id="graphrag-send-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
        </div>
      </div>
    `;
    
    document.body.appendChild(container);
    
    // Position widget
    const position = state.config.position || 'bottom-right';
    container.classList.add(`graphrag-position-${position}`);
    
    // Set primary color
    const primaryColor = state.config.primaryColor || '#3B82F6';
    container.style.setProperty('--primary-color', primaryColor);
    
    // Attach event listeners
    attachEventListeners();
  }
  
  // Attach event listeners
  function attachEventListeners() {
    const toggleBtn = document.getElementById('graphrag-chat-toggle');
    const closeBtn = document.getElementById('graphrag-close-btn');
    const sendBtn = document.getElementById('graphrag-send-btn');
    const input = document.getElementById('graphrag-chat-input');
    
    toggleBtn.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);
    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });
  }
  
  // Toggle chat window
  function toggleChat() {
    state.isOpen = !state.isOpen;
    const window = document.getElementById('graphrag-chat-window');
    const button = document.getElementById('graphrag-chat-toggle');
    
    if (state.isOpen) {
      window.style.display = 'flex';
      button.style.display = 'none';
      document.getElementById('graphrag-chat-input').focus();
    } else {
      window.style.display = 'none';
      button.style.display = 'flex';
    }
  }
  
  // Send message
  async function sendMessage() {
    const input = document.getElementById('graphrag-chat-input');
    const message = input.value.trim();
    
    if (!message || state.isLoading) return;
    
    // Add user message to UI
    addMessage(message, 'user');
    input.value = '';
    
    // Show loading
    state.isLoading = true;
    addLoadingIndicator();
    
    try {
      // Call API
      const response = await fetch(`${state.config.apiUrl}/api/chatbot/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          workspace_id: state.config.workspaceId,
          api_key: state.config.apiKey
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to get response');
      }
      
      const data = await response.json();
      
      // Remove loading indicator
      removeLoadingIndicator();
      
      // Add bot response
      addMessage(data.answer, 'bot');
      
      // Show sources if available
      if (data.sources && data.sources.length > 0) {
        addSources(data.sources);
      }
      
    } catch (error) {
      console.error('Chat error:', error);
      removeLoadingIndicator();
      addMessage('Sorry, I encountered an error. Please try again.', 'bot');
    } finally {
      state.isLoading = false;
    }
  }
  
  // Add message to chat
  function addMessage(text, sender) {
    const messagesContainer = document.getElementById('graphrag-chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `graphrag-message graphrag-${sender}-message`;
    
    const messageText = document.createElement('p');
    messageText.textContent = text;
    messageDiv.appendChild(messageText);
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
  
  // Add sources
  function addSources(sources) {
    const messagesContainer = document.getElementById('graphrag-chat-messages');
    const sourcesDiv = document.createElement('div');
    sourcesDiv.className = 'graphrag-sources';
    
    const sourcesTitle = document.createElement('p');
    sourcesTitle.className = 'graphrag-sources-title';
    sourcesTitle.textContent = 'Sources:';
    sourcesDiv.appendChild(sourcesTitle);
    
    const sourcesList = document.createElement('ul');
    sources.forEach(source => {
      const li = document.createElement('li');
      li.textContent = source;
      sourcesList.appendChild(li);
    });
    
    sourcesDiv.appendChild(sourcesList);
    messagesContainer.appendChild(sourcesDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
  
  // Add loading indicator
  function addLoadingIndicator() {
    const messagesContainer = document.getElementById('graphrag-chat-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'graphrag-message graphrag-bot-message graphrag-loading';
    loadingDiv.id = 'graphrag-loading';
    
    loadingDiv.innerHTML = `
      <div class="graphrag-typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    `;
    
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
  
  // Remove loading indicator
  function removeLoadingIndicator() {
    const loadingDiv = document.getElementById('graphrag-loading');
    if (loadingDiv) {
      loadingDiv.remove();
    }
  }
  
  // Initialize chatbot
  window.GraphRAGChatbot = {
    init: function(config) {
      if (!config.workspaceId || !config.apiKey) {
        console.error('GraphRAG Chatbot: workspaceId and apiKey are required');
        return;
      }
      
      state.config = {
        workspaceId: config.workspaceId,
        apiKey: config.apiKey,
        apiUrl: config.apiUrl || 'http://localhost:8000',
        position: config.position || 'bottom-right',
        primaryColor: config.primaryColor || '#3B82F6',
        title: config.title || 'AI Assistant',
        greeting: config.greeting || 'Hello! How can I help you today?',
        placeholder: config.placeholder || 'Ask a question...'
      };
      
      // Wait for DOM to be ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createWidget);
      } else {
        createWidget();
      }
      
      // Update UI with config
      setTimeout(() => {
        const title = document.getElementById('graphrag-chat-title');
        const greeting = document.getElementById('graphrag-greeting');
        const input = document.getElementById('graphrag-chat-input');
        
        if (title) title.textContent = state.config.title;
        if (greeting) greeting.textContent = state.config.greeting;
        if (input) input.placeholder = state.config.placeholder;
      }, 100);
    }
  };
})();
