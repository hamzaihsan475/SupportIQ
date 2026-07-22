// Module-level HTML escape helper. Copied verbatim from frontend/static/js/listings.js
// (and identical to the one in listing_detail.js). Used at every site where
// user-supplied data is inserted into the DOM via innerHTML to prevent stored
// XSS — security audit fix #2.
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Module-level handle for the escalations tab polling interval. Tracked
// here (outside the DOMContentLoaded closure) so the tab click handler
// can clearInterval() it when navigating away and re-create it on
// return. See startEscalationPolling / stopEscalationPolling below.
let escalationPollInterval = null;

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

            // Polling management: stop on any non-escalations tab so we
            // don't keep hitting /api/admin/escalated in the background.
            // startEscalationPolling() handles both the immediate fetch
            // and the setInterval schedule (5000ms tick). For the
            // escalations tab we skip fetchAndRender() below since
            // startEscalationPolling() already kicked off the load —
            // calling both would fire two back-to-back requests.
            if (target === 'escalations') {
                startEscalationPolling();
            } else {
                stopEscalationPolling();
                await fetchAndRender(target);
            }
        });
    });

    // Starts (or restarts) the escalations polling cycle. Fires an
    // immediate fetch so the panel is populated without waiting for the
    // first tick, then schedules a refresh every 5s. Safe to call when
    // an interval is already running — the prior interval is cleared
    // first to avoid duplicate timers if the user clicks the tab twice.
    function startEscalationPolling() {
        stopEscalationPolling();
        loadEscalations();
        escalationPollInterval = setInterval(loadEscalations, 5000);
    }

    // No-op if no interval is active, so it's safe to call from any
    // tab click without first checking the current state.
    function stopEscalationPolling() {
        if (escalationPollInterval !== null) {
            clearInterval(escalationPollInterval);
            escalationPollInterval = null;
        }
    }

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
                    <td>${escapeHtml(listing.title || listing.address || 'N/A')}</td>
                    <td>${escapeHtml(listing.location || 'N/A')}</td>
                    <td>${listing.price}</td>
                    <td>${escapeHtml(listing.property_type || 'N/A')}</td>
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
                    <td>${escapeHtml(lead.name || 'N/A')}</td>
                    <td>${escapeHtml(lead.budget || 'N/A')}</td>
                    <td>${escapeHtml(lead.contact || 'N/A')}</td>
                    <td>${lead.created_at ? escapeHtml(new Date(lead.created_at).toLocaleDateString()) : 'N/A'}</td>
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

            // Remember which session the admin was viewing so the refresh
            // button can restore the highlight + detail panel afterwards.
            // We read the current active state from the DOM rather than a
            // module variable because the tab can be reloaded multiple
            // times and a single source-of-truth is the rendered panel.
            const previousSelected = document.querySelector(
                '#conv-list-panel .conv-session-item.active'
            );
            const previousSelectedId = previousSelected
                ? previousSelected.getAttribute('data-session')
                : null;

            const listPanel = document.getElementById('conv-list-panel');
            const detailPanel = document.getElementById('conv-detail-panel');
            // Guard against a stale/mismatched DOM (e.g. browser served a
            // cached admin.html that still has the pre-redesign single
            // container). Without this, listPanel.innerHTML = '' below
            // throws "Cannot set properties of null" and the whole
            // loadConversations() fails. We bail with a clear console
            // error so the admin can see what went wrong instead of
            // just a silent blank panel.
            if (!listPanel || !detailPanel) {
                console.error(
                    'Conversations tab DOM mismatch: expected #conv-list-panel '
                    + 'and #conv-detail-panel. The page is likely serving a '
                    + 'stale cached admin.html — hard-refresh (Ctrl+Shift+R) '
                    + 'or clear cache.'
                );
                return;
            }
            listPanel.innerHTML = '';

            const sessionIds = Object.keys(data);
            if (sessionIds.length === 0) {
                listPanel.innerHTML = '<div class="conv-list-empty">No conversations found.</div>';
                renderConversationDetail(null, []);
                return;
            }

            let restoredSelectedId = null;
            sessionIds.forEach(sessionId => {
                const messages = data[sessionId] || [];
                const lastTimestamp = messages.length > 0
                    ? messages[messages.length - 1].timestamp
                    : null;
                const lastTimestampText = lastTimestamp
                    ? formatTimestamp(lastTimestamp)
                    : '—';

                const item = document.createElement('button');
                item.type = 'button';
                item.className = 'conv-session-item';
                item.setAttribute('data-session', sessionId);
                item.innerHTML = `
                    <div class="conv-session-id">${escapeHtml(sessionId)}</div>
                    <div class="conv-session-meta">Last message: ${escapeHtml(lastTimestampText)}</div>
                `;

                if (sessionId === previousSelectedId) {
                    item.classList.add('active');
                    restoredSelectedId = sessionId;
                }

                item.addEventListener('click', () => {
                    document.querySelectorAll('#conv-list-panel .conv-session-item')
                        .forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    renderConversationDetail(sessionId, data[sessionId] || []);
                });

                listPanel.appendChild(item);
            });

            // If the previously selected session is still in the new
            // data, restore its detail view. Otherwise fall back to
            // the placeholder so the right panel doesn't show stale
            // content from a session that no longer exists.
            if (restoredSelectedId) {
                renderConversationDetail(
                    restoredSelectedId,
                    data[restoredSelectedId] || []
                );
            } else {
                renderConversationDetail(null, []);
            }
        } catch (error) {
            console.error('Conversations error:', error);
        }
    }

    // Renders the right-hand detail panel. `sessionId === null` shows the
    // placeholder state. Otherwise renders the session header plus the
    // full message history in the same USER/BOT format as before, then
    // auto-scrolls the detail body to the bottom.
    function renderConversationDetail(sessionId, messages) {
        const detailPanel = document.getElementById('conv-detail-panel');
        // Same guard as in loadConversations() — bail early if the DOM
        // is stale/mismatched instead of crashing on innerHTML = ''.
        if (!detailPanel) {
            console.error('renderConversationDetail: #conv-detail-panel not found in DOM.');
            return;
        }
        detailPanel.innerHTML = '';

        if (sessionId === null) {
            const placeholder = document.createElement('div');
            placeholder.className = 'conv-detail-placeholder';
            placeholder.textContent = 'Select a session to view the conversation.';
            detailPanel.appendChild(placeholder);
            return;
        }

        const header = document.createElement('div');
        header.className = 'conv-detail-header';
        header.textContent = `Session: ${sessionId}`;
        detailPanel.appendChild(header);

        const body = document.createElement('div');
        body.className = 'conv-detail-body';

        if (!messages || messages.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'conv-detail-placeholder';
            empty.textContent = 'No messages in this session.';
            detailPanel.appendChild(body);
            body.appendChild(empty);
            return;
        }

        body.innerHTML = messages.map(m => `
            <div class="log-entry">
                <span class="role ${m.role}">${m.role}</span>
                <span class="text">${escapeHtml(m.message)}</span>
            </div>
        `).join('');

        detailPanel.appendChild(body);

        // Defer scrolling to next frame so the DOM has a chance to lay
        // out the freshly-rendered messages before we measure scrollHeight.
        requestAnimationFrame(() => {
            body.scrollTop = body.scrollHeight;
        });
    }

    // Format a timestamp value for display in the session list. Accepts
    // either an ISO string, an epoch number, or null/undefined. Falls
    // back to the raw value if Date parsing fails so admins still see
    // something useful.
    function formatTimestamp(value) {
        if (value === null || value === undefined || value === '') return '';
        const date = new Date(value);
        if (isNaN(date.getTime())) return String(value);
        return date.toLocaleString();
    }

    async function loadEscalations() {
        try {
            const response = await fetch('/api/admin/escalated');
            if (!response.ok) throw new Error('Escalations fetch failed');
            const data = await response.json();

            const container = document.getElementById('escalated-container');

            // Empty-state short-circuit: no escalations, no DOM to merge
            // against — just render the placeholder.
            if (Object.keys(data).length === 0) {
                container.innerHTML = '<div class="card">No escalated sessions found.</div>';
                return;
            }

            // Determine whether a full rebuild is required. We rebuild
            // when the panel is empty or shows the placeholder card; for
            // every other tick we do a surgical update of the message
            // body for each existing session group. The session-reply
            // block (the input + send button) is never touched during
            // the surgical path, so an admin mid-typing a reply keeps
            // their text, focus, and caret position.
            const existingGroups = container.querySelectorAll('.session-group');
            const needsFullRebuild = existingGroups.length === 0
                || container.querySelector('.card') !== null;

            if (needsFullRebuild) {
                renderEscalationsFull(container, data);
            } else {
                renderEscalationsSurgical(container, data);
            }
        } catch (error) {
            console.error('Escalations error:', error);
        }
    }

    // Full rebuild path: wipes the panel and re-renders every session
    // group, then wires up the resolve / send-reply event listeners.
    // Used on the very first load and whenever a brand-new escalated
    // session appears (its reply input + buttons need to be created).
    function renderEscalationsFull(container, data) {
        container.innerHTML = '';

        Object.entries(data).forEach(([sessionId, messages]) => {
            container.appendChild(buildSessionGroup(sessionId, messages));
        });

        attachEscalationListeners();
    }

    // Surgical update path: for each existing .session-group, refresh
    // only its .session-body (the message list) and scroll it to the
    // bottom if a new message arrived. The .session-reply input is
    // left alone so an admin typing a reply does not have their text
    // wiped. If a session exists in the API response but not in the
    // DOM yet, or vice versa, we fall back to a full rebuild so the
    // set of groups stays consistent and listeners stay attached.
    function renderEscalationsSurgical(container, data) {
        const dataSessionIds = Object.keys(data);
        const existingSessionIds = Array.from(
            container.querySelectorAll('.session-group')
        ).map(g => g.getAttribute('data-session'));

        const sameSet = dataSessionIds.length === existingSessionIds.length
            && dataSessionIds.every(id => existingSessionIds.includes(id));

        if (!sameSet) {
            // A session was added, resolved-and-removed, or both. The
            // simple path can't reconcile that without losing the
            // in-progress reply text, but in practice this is rare and
            // a rebuild keeps the UI correct. We do still try to
            // preserve the active reply value across the rebuild below.
            const activeInput = document.activeElement;
            const preservedValue = (activeInput && activeInput.classList
                && activeInput.classList.contains('reply-input'))
                ? activeInput.value
                : null;
            const preservedSession = preservedValue !== null
                ? activeInput.getAttribute('data-session')
                : null;

            renderEscalationsFull(container, data);

            if (preservedValue !== null) {
                const restored = container.querySelector(
                    `.reply-input[data-session="${preservedSession}"]`
                );
                if (restored) {
                    restored.value = preservedValue;
                    restored.focus();
                }
            }
            return;
        }

        dataSessionIds.forEach(sessionId => {
            const group = container.querySelector(
                `.session-group[data-session="${cssEscape(sessionId)}"]`
            );
            if (!group) {
                return;
            }

            const body = group.querySelector('.session-body');
            if (!body) {
                return;
            }

            const messages = data[sessionId];
            const previousCount = body.querySelectorAll('.log-entry').length;
            const newCount = messages.length;

            body.innerHTML = messages.map(m => `
                <div class="log-entry">
                    <span class="role ${m.role}">${m.role}</span>
                    <span class="text">${escapeHtml(m.message)}</span>
                </div>
            `).join('');

            if (newCount > previousCount) {
                body.scrollTop = body.scrollHeight;
            }
        });
    }

    // Builds a single .session-group element (header + body + reply
    // block) for the given session. Extracted so the full-rebuild path
    // stays readable and there's one source of truth for the markup.
    function buildSessionGroup(sessionId, messages) {
        const group = document.createElement('div');
        group.className = 'session-group';
        group.setAttribute('data-session', sessionId);

        let messagesHtml = messages.map(m => `
            <div class="log-entry">
                <span class="role ${m.role}">${m.role}</span>
                <span class="text">${escapeHtml(m.message)}</span>
            </div>
        `).join('');

        group.innerHTML = `
            <div class="session-header" style="display: flex; justify-content: space-between; align-items: center;">
                <span>Session: ${escapeHtml(sessionId)}</span>
                <button class="btn-secondary resolve-btn" data-session="${escapeHtml(sessionId)}">Mark Resolved</button>
            </div>
            <div class="session-body">${messagesHtml}</div>
            <div class="session-reply" style="padding: 10px; border-top: 1px solid #eee; display: flex; gap: 10px;">
                <input type="text" class="reply-input" data-session="${escapeHtml(sessionId)}" placeholder="Type a reply..." style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                <button class="btn-primary send-reply-btn" data-session="${escapeHtml(sessionId)}" style="width: auto; padding: 8px 16px;">Send Reply</button>
            </div>
        `;
        return group;
    }

    // Wires up the resolve and send-reply buttons after a full rebuild.
    function attachEscalationListeners() {
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
    }

    // Session IDs can contain characters that aren't valid in a CSS
    // attribute selector (e.g. dots, colons, slashes in UUIDs). This
    // delegates to the platform's CSS.escape() if available, with a
    // minimal fallback for older runtimes.
    function cssEscape(value) {
        if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
            return CSS.escape(value);
        }
        return String(value).replace(/[^a-zA-Z0-9_-]/g, '\\$&');
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
        // Send the form as multipart/form-data so the server can receive
        // the attached image files. FormData sets the correct Content-Type
        // (with boundary) automatically — do NOT set it manually.
        const formData = new FormData(addForm);

        // Client-side guard: enforce the 5-image cap and 5 MB limit so the
        // user gets fast feedback. The server re-validates as the source
        // of truth, but this avoids a wasted round-trip.
        const MAX_IMAGES = 5;
        const MAX_FILE_SIZE = 5 * 1024 * 1024;
        const ALLOWED = ['image/jpeg', 'image/png', 'image/webp'];
        const files = formData.getAll('images').filter(f => f && f.name);
        if (files.length > MAX_IMAGES) {
            alert(`You attached ${files.length} images. Maximum is ${MAX_IMAGES}.`);
            return;
        }
        for (const f of files) {
            if (f.size > MAX_FILE_SIZE) {
                const mb = (f.size / (1024 * 1024)).toFixed(2);
                alert(`"${f.name}" is ${mb} MB — maximum is 5 MB.`);
                return;
            }
            const typeOk = (f.type && ALLOWED.includes(f.type))
                || /\.(jpe?g|png|webp)$/i.test(f.name);
            if (!typeOk) {
                alert(`"${f.name}" is not a supported image type (JPG, PNG, WebP).`);
                return;
            }
        }

        try {
            const response = await fetch('/api/admin/listings', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to add listing');
            }

            showNotification('Listing added successfully!');
            addForm.reset();
            await loadListings();
        } catch (error) {
            console.error('Error adding listing:', error);
            alert(error.message || 'Failed to add listing. Please try again.');
        }
    });

    document.getElementById('refresh-listings').addEventListener('click', loadListings);
    document.getElementById('refresh-leads').addEventListener('click', loadLeads);
    document.getElementById('refresh-convs').addEventListener('click', loadConversations);
    document.getElementById('refresh-escalations').addEventListener('click', loadEscalations);

    // Initial load for first active tab
    loadDashboard();

    // If the Escalations tab is the one marked active on page load
    // (e.g. user deep-linked to it, or default tab is changed later),
    // start polling right away. The tab click handler above only fires
    // on user interaction, so without this check the poll would never
    // start until the user clicked the tab.
    const initiallyActiveTab = document.querySelector('.tab-btn.active');
    if (initiallyActiveTab && initiallyActiveTab.getAttribute('data-tab') === 'escalations') {
        startEscalationPolling();
    }
});
