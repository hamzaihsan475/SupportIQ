document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    const addForm = document.getElementById('add-listing-form');

    // State to avoid redundant fetches
    const cache = {
        dashboard: false,
        listings: false,
        leads: false,
        conversations: false,
        escalations: false
    };

    async function fetchAndRender(tabId) {
        switch(tabId) {
            case 'dashboard':
                await loadDashboard();
                break;
            case 'listings':
                await loadListings();
                break;
            case 'leads':
                await loadLeads();
                break;
            case 'conversations':
                await loadConversations();
                break;
            case 'escalations':
                await loadEscalations();
                break;
        }
    }

    // Tab switching logic
    tabs.forEach(tab => {
        tab.addEventListener('click', async () => {
            const target = tab.getAttribute('data-tab');

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            contents.forEach(c => {
                c.classList.remove('active');
                if (c.id === target) c.classList.add('active');
            });

            await fetchAndRender(target);
        });
    });

    function showNotification(message) {
        const notification = document.createElement('div');
        notification.id = 'success-notification';
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    async function loadDashboard() {
        try {
            const response = await fetch('/api/admin/stats');
            if (!response.ok) throw new Error('Stats fetch failed');
            const stats = await response.json();

            document.getElementById('stat-listings').textContent = stats.total_listings;
            document.getElementById('stat-leads').textContent = stats.total_leads;
            document.getElementById('stat-messages').textContent = stats.total_messages;
            document.getElementById('stat-sessions').textContent = stats.unique_sessions;
        } catch (error) {
            console.error('Dashboard error:', error);
        }
    }

    async function loadListings() {
        try {
            const response = await fetch('/api/admin/listings');
            if (!response.ok) throw new Error('Listings fetch failed');
            const listings = await response.json();

            const tableBody = document.querySelector('#listings-table tbody');
            tableBody.innerHTML = '';
            listings.forEach(listing => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${listing.title || listing.address || 'N/A'}</td>
                    <td>${listing.location || 'N/A'}</td>
                    <td>${listing.price}</td>
                    <td>${listing.property_type || 'N/A'}</td>
                    <td>${listing.bedrooms}/${listing.bathrooms}</td>
                `;
                tableBody.appendChild(row);
            });
        } catch (error) {
            console.error('Listings error:', error);
        }
    }

    async function loadLeads() {
        try {
            const response = await fetch('/api/admin/leads');
            if (!response.ok) throw new Error('Leads fetch failed');
            const leads = await response.json();

            const tableBody = document.querySelector('#leads-table tbody');
            tableBody.innerHTML = '';
            leads.forEach(lead => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${lead.name || 'N/A'}</td>
                    <td>${lead.budget || 'N/A'}</td>
                    <td>${lead.contact || 'N/A'}</td>
                    <td>${lead.created_at ? new Date(lead.created_at).toLocaleDateString() : 'N/A'}</td>
                `;
                tableBody.appendChild(row);
            });
        } catch (error) {
            console.error('Leads error:', error);
        }
    }

    async function loadConversations() {
        try {
            const response = await fetch('/api/admin/conversations');
            if (!response.ok) throw new Error('Conversations fetch failed');
            const data = await response.json();

            const container = document.getElementById('conv-container');
            container.innerHTML = '';

            Object.entries(data).forEach(([sessionId, messages]) => {
                const group = document.createElement('div');
                group.className = 'session-group';

                let messagesHtml = messages.map(m => `
                    <div class="log-entry">
                        <span class="role ${m.role}">${m.role}</span>
                        <span class="text">${m.message}</span>
                    </div>
                `).join('');

                group.innerHTML = `
                    <div class="session-header">Session: ${sessionId}</div>
                    <div class="session-body">${messagesHtml}</div>
                `;
                container.appendChild(group);
            });
        } catch (error) {
            console.error('Conversations error:', error);
        }
    }

    async function loadEscalations() {
        try {
            const response = await fetch('/api/admin/escalated');
            if (!response.ok) throw new Error('Escalations fetch failed');
            const data = await response.json();

            const container = document.getElementById('escalated-container');
            container.innerHTML = '';

            if (Object.keys(data).length === 0) {
                container.innerHTML = '<div class="card">No escalated sessions found.</div>';
                return;
            }

            Object.entries(data).forEach(([sessionId, messages]) => {
                const group = document.createElement('div');
                group.className = 'session-group';

                let messagesHtml = messages.map(m => `
                    <div class="log-entry">
                        <span class="role ${m.role}">${m.role}</span>
                        <span class="text">${m.message}</span>
                    </div>
                `).join('');

                group.innerHTML = `
                    <div class="session-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Session: ${sessionId}</span>
                        <button class="btn-secondary resolve-btn" data-session="${sessionId}">Mark Resolved</button>
                    </div>
                    <div class="session-body">${messagesHtml}</div>
                `;
                container.appendChild(group);
            });

            // Add event listeners to resolve buttons
            document.querySelectorAll('.resolve-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const sid = e.target.getAttribute('data-session');
                    await resolveSession(sid);
                });
            });
        } catch (error) {
            console.error('Escalations error:', error);
        }
    }

    async function resolveSession(sessionId) {
        try {
            const response = await fetch(`/api/admin/resolve/${sessionId}`, { method: 'POST' });
            if (!response.ok) throw new Error('Resolve failed');
            showNotification(`Session ${sessionId} marked as resolved!`);
            await loadEscalations();
        } catch (error) {
            console.error('Resolve error:', error);
            alert('Failed to resolve session.');
        }
    }

    addForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(addForm);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/api/admin/listings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) throw new Error('Failed to add listing');

            showNotification('Listing added successfully!');
            addForm.reset();
            await loadListings();
        } catch (error) {
            console.error('Error adding listing:', error);
            alert('Failed to add listing. Please try again.');
        }
    });

    document.getElementById('refresh-listings').addEventListener('click', loadListings);
    document.getElementById('refresh-leads').addEventListener('click', loadLeads);
    document.getElementById('refresh-convs').addEventListener('click', loadConversations);
    document.getElementById('refresh-escalations').addEventListener('click', loadEscalations);

    // Initial load for first active tab
    loadDashboard();
});
