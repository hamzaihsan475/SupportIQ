document.addEventListener('DOMContentLoaded', () => {
    const chatButton = document.getElementById('chat-button');
    const chatWindow = document.getElementById('chat-window');
    const closeButton = document.getElementById('chat-close');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('chat-send');

    let sessionId = localStorage.getItem('supportiq_session_id');
    if (!sessionId) {
        // We don't generate a random one anymore, we wait for the lead capture
    }

    let pollingInterval = null;

    function toggleChat() {
        chatWindow.classList.toggle('hidden');
    }

    function validateAccess() {
        const currentSessionId = localStorage.getItem('supportiq_session_id');
        if (currentSessionId) {
            toggleChat();
        } else {
            document.getElementById('chat-lead-modal').classList.remove('hidden');
        }
    }

    chatButton.addEventListener('click', validateAccess);
    closeButton.addEventListener('click', toggleChat);

    const leadModal = document.getElementById('chat-lead-modal');
    const leadForm = document.getElementById('lead-capture-form');

    leadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('lead-email').value.trim();

        if (validateEmail(email)) {
            localStorage.setItem('supportiq_session_id', email);
            sessionId = email;
            leadModal.classList.add('hidden');
            chatMessages.innerHTML = ''; // Clear history as requested
            toggleChat();
        } else {
            alert('Please enter a valid email address.');
        }
    });

    function validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }


    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('chat-message', sender === 'user' ? 'user-message' : 'bot-message');
        msgDiv.textContent = text;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendTypingIndicator() {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.id = 'typing-indicator';
        indicatorDiv.classList.add('chat-message', 'bot-message', 'typing');
        indicatorDiv.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        chatMessages.appendChild(indicatorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return indicatorDiv;
    }

    async function sendMessage(message) {
        const typingIndicator = appendTypingIndicator();
        chatInput.disabled = true;
        sendButton.disabled = true;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            typingIndicator.remove();

            if (data.response) {
                appendMessage(data.response, 'bot');
            }

            // If the session is escalated, start polling for admin responses
            if (data.intent === 'escalation') {
                startPolling();
            }
        } catch (error) {
            typingIndicator.remove();
            appendMessage('Connection error. Please try again.', 'bot');
        } finally {
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        }
    }

    function startPolling() {
        // Prevent multiple concurrent polling loops
        stopPolling();

        pollingInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/history/${sessionId}`);
                if (!response.ok) throw new Error('History fetch failed');
                const history = await response.json();

                // Smart Termination: Stop polling if no messages are marked as escalated
                const isEscalated = history.some(msg => msg.status === 'escalated');
                if (!isEscalated) {
                    stopPolling();
                    return;
                }

                // Clean Slate: Clear the innerHTML completely before re-rendering
                chatMessages.innerHTML = '';

                // Loop through the entire history chronologically
                history.forEach(msg => {
                    // Explicit Conditional Routing for Roles
                    let senderRole = 'bot'; // Default to left-side (automated/agent)
                    if (msg.role === 'user') {
                        senderRole = 'user'; // Right-side
                    } else if (['bot', 'system', 'admin'].includes(msg.role)) {
                        senderRole = 'bot';   // Left-side
                    }

                    // Only render messages that have content
                    if (msg.message) {
                        appendMessage(msg.message, senderRole);
                    }
                });

                // UI Anchor: Lock onto the freshest exchange
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 3000);
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;

        appendMessage(message, 'user');
        chatInput.value = '';
        sendMessage(message);
    });

    // Initialization: Persist escalation state across reloads
    if (sessionId) {
        (async () => {
            try {
                const response = await fetch(`/api/chat/history/${sessionId}`);
                if (!response.ok) return;
                const history = await response.json();

                const isEscalated = history.some(msg => msg.status === 'escalated');
                if (isEscalated) {
                    // Kick off the live sync loop
                    startPolling();

                    // Immediately render history so user doesn't wait 3 seconds
                    chatMessages.innerHTML = '';
                    history.forEach(msg => {
                        let senderRole = 'bot';
                        if (msg.role === 'user') {
                            senderRole = 'user';
                        } else if (['bot', 'system', 'admin'].includes(msg.role)) {
                            senderRole = 'bot';
                        }
                        if (msg.message) {
                            appendMessage(msg.message, senderRole);
                        }
                    });
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            } catch (error) {
                console.error('Init history error:', error);
            }
        })();
    }
});
