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
                    <button type="button" class="detail-gallery-btn prev" aria-label="Previous image">&lsaquo;</button>
                    <button type="button" class="detail-gallery-btn next" aria-label="Next image">&rsaquo;</button>
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

        // Click-to-zoom on the gallery image. Bound directly on the <img>
        // and stopPropagation() prevents any future ancestor-level handlers
        // from triggering. The CSS scale (1.8) is larger than the card's
        // 1.5 because the detail image is already big — the visual difference
        // is still meaningful. Toggling .detail-gallery--zoom-open on the
        // parent disables the gallery's overflow:hidden so the scaled image
        // isn't clipped back to the original frame.
        img.addEventListener('click', (e) => {
            e.stopPropagation();
            const isZoomed = img.classList.toggle('listing-image--zoomed');
            if (isZoomed) {
                gallery.classList.add('detail-gallery--zoom-open');
            } else {
                gallery.classList.remove('detail-gallery--zoom-open');
            }
        });

        // Carousel handlers attach only when there's something to cycle.
        if (!images || images.length < 2) return;

        let idx = 0;
        function show(newIdx) {
            const n = images.length;
            idx = ((newIdx % n) + n) % n;
            img.src = images[idx];
            if (counter) counter.textContent = `${idx + 1} / ${n}`;
            gallery.setAttribute('data-image-index', String(idx));
        }
        // stopPropagation on the arrow clicks is defensive — there's no
        // ancestor click handler today, but if one is added later it should
        // not fire from an arrow click.
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
            <div class="detail-title-row">
                <h1 class="detail-title">${escapeHtml(data.title || 'Unnamed Property')}${soldBadge}</h1>
            </div>
            <div class="detail-info-grid">
                <div class="detail-info-item">
                    <span class="label">Location</span>
                    <span class="value">${escapeHtml(data.location || 'N/A')}</span>
                </div>
                <div class="detail-info-item">
                    <span class="label">Property Type</span>
                    <span class="value">${escapeHtml(data.property_type || 'N/A')}</span>
                </div>
                <div class="detail-info-item">
                    <span class="label">Area</span>
                    <span class="value">${escapeHtml(data.area || 'N/A')} sq yards</span>
                </div>
                <div class="detail-info-item">
                    <span class="label">Bedrooms</span>
                    <span class="value">${escapeHtml(data.bedrooms || 0)}</span>
                </div>
                <div class="detail-info-item">
                    <span class="label">Bathrooms</span>
                    <span class="value">${escapeHtml(data.bathrooms || 0)}</span>
                </div>
                <div class="detail-info-item price">
                    <span class="label">Price</span>
                    <span class="value">${formatPKR(data.price)}</span>
                </div>
            </div>
            <section class="detail-contact" aria-labelledby="contact-heading">
                <h2 id="contact-heading">Contact Submitter</h2>
                <div class="detail-contact-row">
                    <div>
                        <span class="label">Name</span>
                        <span class="value">${escapeHtml(contactName)}</span>
                    </div>
                    <div>
                        <span class="label">Contact</span>
                        <span class="value">${escapeHtml(contactValue)}</span>
                    </div>
                </div>
            </section>
        `;
        attachGalleryHandlers(data.images || []);
    }

    try {
        const response = await fetch(`/listings/${encodeURIComponent(listingId)}`);
        if (response.status === 404) {
            renderError('Listing not found');
            return;
        }
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        renderDetail(data);
    } catch (error) {
        console.error('Detail fetch error:', error);
        renderError('Unable to load this listing');
    }
});