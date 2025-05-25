// MediBot JavaScript functionality
class MediBot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.wellnessPlanModal = document.getElementById('wellnessPlanModal');
        this.closeModal = document.getElementById('closeModal');
        this.startNewChat = document.getElementById('startNewChat');
        this.charCount = document.querySelector('.char-count');
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupCharacterCounter();
        this.focusInput();
    }
    
    setupEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        if (this.closeModal) {
            this.closeModal.addEventListener('click', () => this.hideWellnessPlan());
        }
        
        if (this.startNewChat) {
            this.startNewChat.addEventListener('click', () => {
                window.location.href = '/';
            });
        }
        
        if (this.wellnessPlanModal) {
            this.wellnessPlanModal.addEventListener('click', (e) => {
                if (e.target === this.wellnessPlanModal) {
                    this.hideWellnessPlan();
                }
            });
        }
    }
    
    setupCharacterCounter() {
        this.messageInput.addEventListener('input', () => {
            const count = this.messageInput.value.length;
            this.charCount.textContent = `${count}/1000`;
            
            if (count > 900) {
                this.charCount.style.color = '#e74c3c';
            } else if (count > 700) {
                this.charCount.style.color = '#f39c12';
            } else {
                this.charCount.style.color = '#7f8c8d';
            }
        });
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        this.clearInput();
        
        // Show loading state
        this.setLoadingState(true);
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            if (data.error) {
                this.addMessage(`Sorry, there was an error: ${data.error}`, 'bot', true);
            } else {
                this.addMessage(data.response, 'bot');
                
                if (data.action === 'show_plan') {
                    setTimeout(() => this.showWellnessPlan(data.response), 500);
                }
            }
        } catch (error) {
            this.addMessage('Sorry, there was a connection error. Please try again.', 'bot', true);
        } finally {
            this.setLoadingState(false);
        }
    }
    
    addMessage(message, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message ${isError ? 'error' : ''}`;
        
        if (sender === 'bot') {
            messageDiv.innerHTML = `
                <div class="bot-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">${this.formatMessage(message)}</div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-content">
                    <div class="message-text">${message}</div>
                </div>
                <div class="user-avatar">
                    <i class="fas fa-user"></i>
                </div>
            `;
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Add typing animation for bot messages
        if (sender === 'bot') {
            this.animateTyping(messageDiv.querySelector('.message-text'));
        }
    }
    
    formatMessage(message) {
        return message
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }
    
    animateTyping(element) {
        const text = element.innerHTML;
        element.innerHTML = '';
        let i = 0;
        
        const typewriter = () => {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
                setTimeout(typewriter, 10); // Adjust speed as needed
            }
        };
        
        typewriter();
    }
    
    clearInput() {
        this.messageInput.value = '';
        this.charCount.textContent = '0/1000';
        this.charCount.style.color = '#7f8c8d';
    }
    
    setLoadingState(isLoading) {
        if (isLoading) {
            this.loadingOverlay.style.display = 'flex';
            this.sendButton.disabled = true;
        } else {
            this.loadingOverlay.style.display = 'none';
            this.sendButton.disabled = false;
            this.messageInput.focus();
        }
    }
    
    showWellnessPlan(content) {
        const planContent = content.split('PRELIMINARY WELLNESS PLAN:')[1] || content;
        document.getElementById('wellnessPlanContent').innerHTML = 
            `<div class="wellness-plan">${this.formatMessage(planContent)}</div>`;
        this.wellnessPlanModal.style.display = 'flex';
    }
    
    hideWellnessPlan() {
        this.wellnessPlanModal.style.display = 'none';
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    focusInput() {
        window.addEventListener('load', () => {
            this.messageInput.focus();
        });
    }
}

// Initialize MediBot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MediBot();
});

// Add some utility functions for enhanced UX
function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="bot-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="typing-animation">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return typingDiv;
}

function removeTypingIndicator() {
    const indicator = document.querySelector('.typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}
