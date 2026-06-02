document.addEventListener('DOMContentLoaded', () => {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    const loadedTabs = new Set();

    // --- Tab Switching Logic ---
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;

            // Update Buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update Panes
            tabPanes.forEach(p => {
                p.classList.remove('active');
                if (p.id === targetTab) p.classList.add('active');
            });

            // Lazy Load Data
            if (!loadedTabs.has(targetTab)) {
                loadTabData(targetTab);
                loadedTabs.add(targetTab);
            }
        });
    });

    // Initial load for Dashboard
    loadTabData('dashboard');
    loadedTabs.add('dashboard');

    async function loadTabData(tab) {
        try {
            if (tab === 'dashboard') {
                const res = await fetch('/api/admin/stats');
                const data = await res.json();
                document.getElementById('stat-listings').textContent = data.total_listings;
                document.getElementById('stat-leads').textContent = data.total_leads;
                document.getElementById('stat-convs').textContent = data.total_conversations;
                document.getElementById('stat-sessions').textContent = data.unique_sessions;
            } else if (tab === 'listings') {
                const res = await fetch('/api/admin/listings');
                const data = await res.json();
                const tbody = document.querySelector('#listings-table tbody');
                tbody.innerHTML = '';
                data.forEach(item => {
                    const row = `<tr>
                        <td>${item.id}</td>
                        <td>${item.title || 'N/A'}</td>
                        <td>${item.location || 'N/A'}</td>
                        <td>${item.area || 'N/A'}</td>
                        <td>${item.property_type || 'N/A'}</td>
                        <td>${item.price || 'N/A'}</td>
                        <td>${item.bedrooms || 'N/A'}</td>
                        <td>${item.bathrooms || 'N/A'}</td>
                        <td>${item.status || 'N/A'}</td>
                    </tr>`;
                    tbody.insertAdjacentHTML('beforeend', row);
                });
            } else if (tab === 'leads') {
                const res = await fetch('/api/admin/leads');
                const data = await res.json();
                const tbody = document.querySelector('#leads-table tbody');
                tbody.innerHTML = '';
                data.forEach(item => {
                    const date = item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A';
                    const row = `<tr>
                        <td>${item.name || 'N/A'}</td>
                        <td>${item.budget || 'N/A'}</td>
                        <td>${item.contact || 'N/A'}</td>
                        <td>${date}</td>
                    </tr>`;
                    tbody.insertAdjacentHTML('beforeend', row);
                });
            } else if (tab === 'conversations') {
                await loadConversations();
            }
        } catch (err) {
            console.error(`Error loading ${tab} data:`, err);
        }
    }

    // --- Conversation Handling ---
    let conversationData = [];

    async function loadConversations() {
        try {
            const res = await fetch('/api/admin/conversations');
            conversationData = await res.json();
            const list = document.getElementById('session-list');
            list.innerHTML = '';

            conversationData.forEach((session, index) => {
                const item = document.createElement('div');
                item.className = 'session-item';
                item.textContent = `Session: ${session.session_id}`;
                item.onclick = () => {
                    document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    displayMessages(session.session_id);
                };
                list.appendChild(item);
            });
        } catch (err) {
            console.error('Error loading conversations:', err);
        }
    }

    function displayMessages(sessionId) {
        const session = conversationData.find(s => s.session_id === sessionId);
        const display = document.getElementById('chat-display');
        display.innerHTML = '';

        if (!session || !session.messages.length) {
            display.innerHTML = '<div class="chat-placeholder">No messages found for this session</div>';
            return;
        }

        session.messages.forEach(msg => {
            const bubble = document.createElement('div');
            bubble.className = `msg-bubble ${msg.role === 'user' ? 'msg-user' : 'msg-bot'}`;
            bubble.textContent = msg.message;
            display.appendChild(bubble);
        });

        // Scroll to bottom
        display.scrollTop = display.scrollHeight;
    }
});
