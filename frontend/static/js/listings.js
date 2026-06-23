document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('listings-container');
    if (!container) return;

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

    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Build the image carousel HTML for a single listing card. Two cases:
    //   - 0 images: a clean placeholder div, no controls.
    //   - 1+ images: a single <img> with prev/next arrows and a "1 / N" counter.
    // The current index is stored on a data-attribute on the wrap so the
    // click handlers can read/write it without any extra state.
    function renderImageArea(listing) {
        const images = Array.isArray(listing.images) ? listing.images : [];
        if (images.length === 0) {
            return `
                <div class="listing-image-wrap" data-listing-id="${listing.id}" data-image-index="0">
                    <div class="listing-image-placeholder">No image available</div>
                </div>
            `;
        }
        const safeFirst = escapeHtml(images[0]);
        const hasMultiple = images.length > 1;
        return `
            <div class="listing-image-wrap" data-listing-id="${listing.id}" data-image-index="0" data-image-count="${images.length}">
                <img class="listing-image" src="${safeFirst}" alt="${escapeHtml(listing.title || 'Property image')}">
                ${hasMultiple ? `
                    <button type="button" class="listing-carousel-btn prev" aria-label="Previous image">‹</button>
                    <button type="button" class="listing-carousel-btn next" aria-label="Next image">›</button>
                    <span class="listing-image-counter">1 / ${images.length}</span>
                ` : ''}
            </div>
        `;
    }

    // Pure-vanilla carousel: cycle the visible <img> src on arrow click.
    // Reads images from a JSON-encoded data attribute (set on the wrap at
    // render time) so we never need to re-fetch the API for a cycle.
    function attachCarouselHandlers(container) {
        container.querySelectorAll('.listing-image-wrap').forEach(wrap => {
            const count = parseInt(wrap.getAttribute('data-image-count') || '0', 10);

            const img = wrap.querySelector('img');
            if (!img) return;

            // Read images off the parent card — the same data attribute the
            // arrow-cycling logic uses. Falls back to a single-element array
            // so single-image cards still get a (no-op) carousel path that
            // doesn't error.
            const card = wrap.closest('.listing-card');
            let images = [];
            if (card) {
                try {
                    images = JSON.parse(card.getAttribute('data-images') || '[]');
                } catch (_) { images = []; }
            }

            // Click-to-zoom on the image itself. Bound directly on the <img>
            // so e.stopPropagation() reliably prevents the click from bubbling
            // up to the card-level navigation handler on the container. Toggling
            // the .listing-image--zoomed class triggers the CSS scale, and we
            // toggle .listing-image-wrap--zoom-open on the parent so the wrap's
            // overflow:hidden doesn't clip the scaled image. This runs for
            // every card (single- or multi-image) so zoom is always available.
            img.addEventListener('click', (e) => {
                e.stopPropagation();
                const isZoomed = img.classList.toggle('listing-image--zoomed');
                if (isZoomed) {
                    wrap.classList.add('listing-image-wrap--zoom-open');
                } else {
                    wrap.classList.remove('listing-image-wrap--zoom-open');
                }
            });

            // Carousel arrow handlers only attach when there's actually
            // something to cycle through. Single-image cards don't render
            // arrow buttons in renderImageArea() either, so this is the
            // matching skip.
            if (!count || images.length < 2) return;

            const prevBtn = wrap.querySelector('.listing-carousel-btn.prev');
            const nextBtn = wrap.querySelector('.listing-carousel-btn.next');
            const counter = wrap.querySelector('.listing-image-counter');

            let idx = 0;

            function show(newIdx) {
                const n = images.length;
                idx = ((newIdx % n) + n) % n;
                img.src = images[idx];
                if (counter) counter.textContent = `${idx + 1} / ${n}`;
                wrap.setAttribute('data-image-index', String(idx));
            }

            if (prevBtn) prevBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                show(idx - 1);
            });
            if (nextBtn) nextBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                show(idx + 1);
            });
        });
    }

    try {
        const response = await fetch('/listings/');
        if (!response.ok) throw new Error('Network response was not ok');

        const listings = await response.json();

        if (listings.length === 0) {
            container.innerHTML = '<p class="no-listings">No listings available at the moment.</p>';
            return;
        }

        container.innerHTML = '';
        listings.forEach(listing => {
            const card = document.createElement('div');
            card.className = 'listing-card' + (listing.is_sold ? ' listing-card-sold' : '');
            // Stash the image URLs as a JSON data-attribute so the carousel
            // handlers can cycle through them without touching the API again.
            card.setAttribute('data-images', JSON.stringify(listing.images || []));
            // Identifier used by the delegated click handler to navigate to
            // this listing's detail page.
            card.setAttribute('data-listing-id', String(listing.id));
            // Make the card keyboard-focusable so it's reachable without a mouse.
            card.setAttribute('role', 'link');
            card.setAttribute('tabindex', '0');
            const soldBadge = listing.is_sold
                ? ' <span class="listing-sold-badge">SOLD</span>'
                : '';
            const imageArea = renderImageArea(listing);
            card.innerHTML = `
                ${imageArea}
                <h3 class="listing-title">${escapeHtml(listing.title || listing.address || 'Unnamed Property')}${soldBadge}</h3>
                <p><strong class="label">Location:</strong> ${escapeHtml(listing.location || listing.address || 'N/A')}</p>
                <p><strong class="label">Type:</strong> ${escapeHtml(listing.property_type || 'N/A')}</p>
                <p><strong class="label">Area:</strong> ${escapeHtml(listing.area || 'N/A')} sq yards</p>
                <p><strong class="label">Rooms:</strong> ${escapeHtml(listing.bedrooms || 0)} Bed | ${escapeHtml(listing.bathrooms || 0)} Bath</p>
                <p class="listing-price"><strong class="label">Price:</strong> ${formatPKR(listing.price)}</p>
            `;
            container.appendChild(card);
        });

        attachCarouselHandlers(container);

        // Delegated click handler: clicking anywhere on a card navigates to
        // its detail page. The carousel arrow handlers above call
        // e.stopPropagation(), so they prevent this handler from firing when
        // the user clicks a carousel button — required by the feature spec.
        function navigateToCard(card) {
            const id = card.getAttribute('data-listing-id');
            if (!id) return;
            window.location.href = `/listings/view/${encodeURIComponent(id)}`;
        }
        container.addEventListener('click', (e) => {
            const card = e.target.closest('.listing-card');
            if (!card) return;
            navigateToCard(card);
        });
        // Keyboard support: Enter or Space on a focused card triggers nav,
        // matching the role="link" affordance. Arrows are excluded by the
        // carousel-button shortcut below — but those buttons have their own
        // click handlers, not key handlers, so we just bail on Space/Enter
        // when the focus is on a carousel button.
        container.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            // If a carousel button has focus, let it (no key handler there)
            // but we still don't want the card-level handler firing.
            if (e.target.classList && e.target.classList.contains('listing-carousel-btn')) {
                return;
            }
            const card = e.target.closest('.listing-card');
            if (!card) return;
            e.preventDefault();
            navigateToCard(card);
        });
    } catch (error) {
        console.error('Error fetching listings:', error);
        container.innerHTML = '<p>Error loading listings. Please try again later.</p>';
    }
});
