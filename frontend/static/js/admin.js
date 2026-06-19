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

            const activeFilter = document.querySelector('#listings-status-filter .status-filter-btn.active');
            const filterValue = activeFilter ? activeFilter.getAttribute('data-filter') : 'all';

            const visible = listings.filter(l => {
                const status = (l.status || 'approved').toLowerCase();
                if (filterValue === 'all') return true;
                return status === filterValue;
            });

            if (visible.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="7" style="text-align:center; color:#64748B; padding:20px;">No listings match this filter.</td>`;
                tableBody.appendChild(row);
                return;
            }

            visible.forEach(listing => {
                const status = (listing.status || 'approved').toLowerCase();
                const statusClass = ['pending', 'approved', 'rejected', 'deleted'].includes(status)
                    ? status
                    : 'available';
                const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
                const isSold = !!listing.is_sold;

                let actionsHtml;
                if (status === 'pending') {
                    actionsHtml = `
                        <button class="listing-action-btn approve" data-listing-id="${listing.id}">Approve</button>
                        <button class="listing-action-btn reject" data-listing-id="${listing.id}">Reject</button>
                    `;
                } else if (status === 'approved') {
                    const soldBtnClass = isSold ? 'mark-unsold' : 'mark-sold';
                    const soldBtnLabel = isSold ? 'Mark Unsold' : 'Mark Sold';
                    actionsHtml = `
                        <button class="listing-action-btn ${soldBtnClass}" data-listing-id="${listing.id}">${soldBtnLabel}</button>
                        <button class="listing-action-btn delete" data-listing-id="${listing.id}">Delete</button>
                    `;
                } else {
                    actionsHtml = '<span style="color:#64748B; font-size:12px;">—</span>';
                }

                const soldBadge = isSold ? ' <span class="status-badge sold">Sold</span>' : '';

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${listing.title || listing.address || 'N/A'}</td>
                    <td>${listing.location || 'N/A'}</td>
                    <td>${listing.price}</td>
                    <td>${listing.property_type || 'N/A'}</td>
                    <td>${listing.bedrooms}/${listing.bathrooms}</td>
                    <td><span class="status-badge ${statusClass}">${statusLabel}</span>${soldBadge}</td>
                    <td>${actionsHtml}</td>
                `;
                tableBody.appendChild(row);
            });

            tableBody.querySelectorAll('.listing-action-btn.approve').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-listing-id');
                    await moderateListing(id, 'approve');
                });
            });
            tableBody.querySelectorAll('.listing-action-btn.reject').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-listing-id');
                    await moderateListing(id, 'reject');
                });
            });
            tableBody.querySelectorAll('.listing-action-btn.mark-sold, .listing-action-btn.mark-unsold').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-listing-id');
                    const action = e.target.classList.contains('mark-sold') ? 'mark-sold' : 'mark-unsold';
                    await moderateListing(id, action);
                });
            });
            tableBody.querySelectorAll('.listing-action-btn.delete').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-listing-id');
                    await deleteListing(id);
                });
            });
        } catch (error) {
            console.error('Listings error:', error);
        }
    }

    async function moderateListing(listingId, action) {
        try {
            const response = await fetch(`/api/admin/listings/${listingId}/${action}`, { method: 'POST' });
            if (!response.ok) throw new Error(`${action} failed`);
            const friendly = action.replace(/-/g, ' ');
            showNotification(`Listing ${listingId} ${friendly}!`);
            await loadListings();
        } catch (error) {
            console.error(`${action} error:`, error);
            alert(`Failed to ${action} listing.`);
        }
    }

    async function deleteListing(listingId) {
        if (!confirm('Are you sure you want to delete this listing?')) return;
        try {
            const response = await fetch(`/api/admin/listings/${listingId}/delete`, { method: 'POST' });
            if (!response.ok) throw new Error('delete failed');
            showNotification(`Listing ${listingId} deleted!`);
            await loadListings();
        } catch (error) {
            console.error('delete error:', error);
            alert('Failed to delete listing.');
        }
    }

    document.querySelectorAll('#listings-status-filter .status-filter-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            document.querySelectorAll('#listings-status-filter .status-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            await loadListings();
        });
    });

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
                    <div class="session-reply" style="padding: 10px; border-top: 1px solid #eee; display: flex; gap: 10px;">
                        <input type="text" class="reply-input" data-session="${sessionId}" placeholder="Type a reply..." style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        <button class="btn-primary send-reply-btn" data-session="${sessionId}" style="width: auto; padding: 8px 16px;">Send Reply</button>
                    </div>
                `;
                container.appendChild(group);
            });

            document.querySelectorAll('.resolve-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const sid = e.target.getAttribute('data-session');
                    await resolveSession(sid);
                });
            });

            document.querySelectorAll('.send-reply-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const sid = e.target.getAttribute('data-session');
                    const input = document.querySelector(`.reply-input[data-session="${sid}"]`);
                    await sendReply(sid, input.value);
                });
            });
        } catch (error) {
            console.error('Escalations error:', error);
        }
    }

    async function sendReply(sessionId, messageText) {
        if (!messageText.trim()) return;
        try {
            const response = await fetch('/api/admin/send-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    message_text: messageText
                })
            });
            if (!response.ok) throw new Error('Send reply failed');
            showNotification(`Reply sent to ${sessionId}!`);
            await loadEscalations();
        } catch (error) {
            console.error('Send reply error:', error);
            alert('Failed to send reply.');
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
