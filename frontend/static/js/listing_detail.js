document.addEventListener('DOMContentLoaded', async () => {
    const root = document.getElementById('detail-content');
    if (!root) return;

    const listingId = window.__LISTING_ID__;

    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatPKR(price) {
        const val = parseFloat(price);
        if (isNaN(val)) return 'N/A';
        if (val >= 10000000) {
            return (val / 10000000).toFixed(2) + ' Crore';
        } else if (val >= 100000) {
            return (val / 100000).toFixed(2) + ' Lakh';
        } else {
            return val.toLocaleString('en-PK') + ' PKR';
        }
    }

    function renderError(message) {
        root.innerHTML = `
            <div class="detail-error">
                <h2>${escapeHtml(message)}</h2>
                <p>The listing may have been removed, or the link is incorrect.</p>
            </div>
        `;
    }

    function renderGallery(images, altTitle) {
        const list = Array.isArray(images) ? images : [];
        if (list.length === 0) {
            return `
                <div class="detail-gallery" data-image-index="0">
                    <div class="listing-image-placeholder">No image available</div>
                </div>
            `;
        }
        const safeFirst = escapeHtml(list[0]);
        const hasMultiple = list.length > 1;
        return `
            <div class="detail-gallery" data-image-index="0" data-image-count="${list.length}">
                <img class="listing-image" src="${safeFirst}" alt="${escapeHtml(altTitle || 'Property image')}">
                ${hasMultiple ? `
                    <button type="button" class="detail-gallery-btn prev" aria-label="Previous image">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                    </button>
                    <button type="button" class="detail-gallery-btn next" aria-label="Next image">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                    </button>
                    <span class="detail-gallery-counter">1 / ${list.length}</span>
                ` : ''}
            </div>
        `;
    }

    function attachGalleryHandlers(images) {
        const gallery = root.querySelector('.detail-gallery');
        if (!gallery) return;
        const count = parseInt(gallery.getAttribute('data-image-count') || '0', 10);
        if (!count) return;

        const img = gallery.querySelector('img');
        const prevBtn = gallery.querySelector('.detail-gallery-btn.prev');
        const nextBtn = gallery.querySelector('.detail-gallery-btn.next');
        const counter = gallery.querySelector('.detail-gallery-counter');
        if (!img) return;

        img.addEventListener('click', (e) => {
            e.stopPropagation();
            const isZoomed = img.classList.toggle('listing-image--zoomed');
            if (isZoomed) {
                gallery.classList.add('detail-gallery--zoom-open');
            } else {
                gallery.classList.remove('detail-gallery--zoom-open');
            }
        });

        if (!images || images.length < 2) return;

        let idx = 0;
        function show(newIdx) {
            const n = images.length;
            idx = ((newIdx % n) + n) % n;
            img.src = images[idx];
            if (counter) counter.textContent = `${idx + 1} / ${n}`;
            gallery.setAttribute('data-image-index', String(idx));
        }
        if (prevBtn) prevBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            show(idx - 1);
        });
        if (nextBtn) nextBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            show(idx + 1);
        });
    }

    function renderDetail(data) {
        const soldBadge = data.is_sold
            ? ' <span class="listing-sold-badge">SOLD</span>'
            : '';
        const contactName = data.submitter_name || 'N/A';
        const contactValue = data.submitter_contact || 'N/A';

        root.innerHTML = `
            ${renderGallery(data.images, data.title)}
            <div class="detail-hero">
                <div class="detail-hero-content">
                    <h1 class="detail-title">${escapeHtml(data.title || 'Unnamed Property')}${soldBadge}</h1>
                    <p class="detail-subtitle">${escapeHtml(data.location || 'N/A')}</p>
                    <div class="detail-price-tag">${formatPKR(data.price)}</div>
                </div>
                <div class="detail-hero-actions">
                    <button class="btn btn-primary" id="ask-about-property">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px; vertical-align: middle;"><path d="m21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        Ask about this property
                    </button>
                </div>
            </div>
            <div class="detail-quick-facts">
                <div class="fact-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
                    <span><strong>Type:</strong> ${escapeHtml(data.property_type || 'N/A')}</span>
                </div>
                <div class="fact-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                    <span><strong>Area:</strong> ${escapeHtml(data.area || 'N/A')} sq yards</span>
                </div>
                <div class="fact-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-12-8-12a2 2 0 0 1-2-2c0-1 1-3 2-4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2c0 1 1 3 2 4a2 2 0 0 1-2 2Z"/><path d="M12 12v.01"/><path d="M16 12v.01"/><path d="M8 12v.01"/></svg>
                    <span><strong>Bedrooms:</strong> ${escapeHtml(data.bedrooms || 0)}</span>
                </div>
                <div class="fact-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12a8 8 0 0 1 8-8v8"/><path d="M16 12a8 8 0 0 1-8 8v-8"/></svg>
                    <span><strong>Bathrooms:</strong> ${escapeHtml(data.bathrooms || 0)}</span>
                </div>
            </div>
            <section class="detail-contact" aria-labelledby="contact-heading">
                <h2 id="contact-heading">Contact Submitter</h2>
                <div class="detail-contact-row">
                    <div class="contact-box">
                        <span class="label">Name</span>
                        <span class="value">${escapeHtml(contactName)}</span>
                    </div>
                    <div class="contact-box">
                        <span class="label">Contact</span>
                        <span class="value">${escapeHtml(contactValue)}</span>
                    </div>
                </div>
            </section>
        `;
        attachGalleryHandlers(data.images || []);

        document.getElementById('ask-about-property')?.addEventListener('click', () => {
            if (window.openChatWithContext) {
                window.openChatWithContext(data.title);
            } else {
                document.getElementById('chat-button')?.click();
            }
        });
    }

    try {
        const response = await fetch(`/listings/${encodeURIComponent(listingId)}`);
        if (response.status === 404) {
            renderError('Listing not found');
            } else if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        } else {
            const data = await response.json();
            renderDetail(data);
        }
    } catch (error) {
        console.error('Detail fetch error:', error);
        renderError('Unable to load this listing');
    }
});
