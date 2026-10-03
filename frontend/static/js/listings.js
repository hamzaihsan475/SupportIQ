document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('listings-container');
    if (!container) return;

    // State management for filtering/sorting
    let allListings = [];
    let filteredListings = [];

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
                    <button type="button" class="listing-carousel-btn prev" aria-label="Previous image">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                    </button>
                    <button type="button" class="listing-carousel-btn next" aria-label="Next image">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                    </button>
                    <span class="listing-image-counter">1 / ${images.length}</span>
                ` : ''}
            </div>
        `;
    }

    function attachCarouselHandlers(container) {
        container.querySelectorAll('.listing-image-wrap').forEach(wrap => {
            const count = parseInt(wrap.getAttribute('data-image-count') || '0', 10);
            const img = wrap.querySelector('img');
            if (!img) return;

            const card = wrap.closest('.listing-card');
            let images = [];
            if (card) {
                try {
                    images = JSON.parse(card.getAttribute('data-images') || '[]');
                } catch (_) { images = []; }
            }

            img.addEventListener('click', (e) => {
                e.stopPropagation();
                const isZoomed = img.classList.toggle('listing-image--zoomed');
                if (isZoomed) {
                    wrap.classList.add('listing-image-wrap--zoom-open');
                } else {
                    wrap.classList.remove('listing-image-wrap--zoom-open');
                }
            });

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

    async function fetchAndRender() {
        try {
            const response = await fetch('/listings/');
            if (!response.ok) throw new Error('Network response was not ok');

            allListings = await response.json();
            applyFiltersAndSort();
        } catch (error) {
            console.error('Error fetching listings:', error);
            UIState.showError(container, 'Failed to load listings. Please try again later.', () => location.reload());
        }
    }

    function applyFiltersAndSort() {
        const type = document.getElementById('filter-type')?.value;
        const minPrice = parseFloat(document.getElementById('filter-min-price')?.value) || 0;
        const maxPrice = parseFloat(document.getElementById('filter-max-price')?.value) || Infinity;
        const minBeds = parseInt(document.getElementById('filter-beds')?.value) || 0;
        const minBaths = parseInt(document.getElementById('filter-baths')?.value) || 0;
        const sort = document.getElementById('sort-price')?.value;
        const locationQuery = document.getElementById('listings-location')?.value.toLowerCase().trim();

        filteredListings = allListings.filter(l => {
            const matchType = !type || l.property_type === type;
            const matchPrice = l.price >= minPrice && l.price <= maxPrice;
            const matchBeds = (l.bedrooms || 0) >= minBeds;
            const matchBaths = (l.bathrooms || 0) >= minBaths;
            const matchLoc = !locationQuery ||
                (l.location && l.location.toLowerCase().includes(locationQuery)) ||
                (l.address && l.address.toLowerCase().includes(locationQuery));

            return matchType && matchPrice && matchBeds && matchBaths && matchLoc;
        });

        if (sort === 'price_asc') {
            filteredListings.sort((a, b) => a.price - b.price);
        } else if (sort === 'price_desc') {
            filteredListings.sort((a, b) => b.price - a.price);
        } else if (sort === 'newest') {
            // Assuming API provides created_at, otherwise default sort
            filteredListings.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        }

        updateUI();
    }

    function updateUI() {
        const countEl = document.getElementById('result-count');
        if (countEl) countEl.textContent = `${filteredListings.length} homes found`;

        if (filteredListings.length === 0) {
            UIState.showEmpty(container, 'No properties match your filters.');
            return;
        }

        renderListings(filteredListings);
    }

    function renderListings(listings) {
        container.innerHTML = '';
        listings.forEach(listing => {
            const card = document.createElement('div');
            card.className = 'listing-card' + (listing.is_sold ? ' listing-card-sold' : '');
            card.setAttribute('data-images', JSON.stringify(listing.images || []));
            card.setAttribute('data-listing-id', String(listing.id));
            card.setAttribute('role', 'link');
            card.setAttribute('tabindex', '0');

            const soldBadge = listing.is_sold ? ' <span class="listing-sold-badge">SOLD</span>' : '';
            const imageArea = renderImageArea(listing);

            card.innerHTML = `
                ${imageArea}
                <div class="listing-card-body">
                    <h3 class="listing-title">${escapeHtml(listing.title || listing.address || 'Unnamed Property')}${soldBadge}</h3>
                    <p><strong class="label">Location:</strong> ${escapeHtml(listing.location || listing.address || 'N/A')}</p>
                    <p><strong class="label">Type:</strong> ${escapeHtml(listing.property_type || 'N/A')}</p>
                    <p><strong class="label">Area:</strong> ${escapeHtml(listing.area || 'N/A')} sq yards</p>
                    <p><strong class="label">Rooms:</strong> ${escapeHtml(listing.bedrooms || 0)} Bed | ${escapeHtml(listing.bathrooms || 0)} Bath</p>
                    <p class="listing-price"><strong class="label">Price:</strong> ${formatPKR(listing.price)}</p>
                </div>
            `;
            container.appendChild(card);
        });

        attachCarouselHandlers(container);
    }

    // Event Listeners for Filters
    ['filter-type', 'filter-min-price', 'filter-max-price', 'filter-beds', 'filter-baths', 'sort-price'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', applyFiltersAndSort);
        document.getElementById(id)?.addEventListener('input', applyFiltersAndSort);
    });

    document.getElementById('clear-filters')?.addEventListener('click', () => {
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-min-price').value = '';
        document.getElementById('filter-max-price').value = '';
        document.getElementById('filter-beds').value = '';
        document.getElementById('filter-baths').value = '';
        document.getElementById('sort-price').value = 'default';
        applyFiltersAndSort();
    });

    const searchForm = document.getElementById('listings-search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            applyFiltersAndSort();
        });
    }

    // Search Input Autocomplete (Existing logic preserved)
    const locationInput = document.getElementById('listings-location');
    const autocomplete = document.getElementById('listings-autocomplete');
    if (locationInput && autocomplete) {
        locationInput.addEventListener('input', async (e) => {
            const query = e.target.value.trim();
            if (query.length < 2) {
                autocomplete.classList.add('hidden');
                return;
            }
            try {
                const resp = await fetch(`/api/locations?q=${encodeURIComponent(query)}`);
                const locations = await resp.json();
                if (locations.length === 0) {
                    autocomplete.classList.add('hidden');
                    return;
                }
                autocomplete.innerHTML = locations.map(loc =>
                    `<div class="autocomplete-item" data-val="${loc}">${loc}</div>`
                ).join('');
                autocomplete.classList.remove('hidden');
            } catch (err) { console.error('Autocomplete error:', err); }
        });

        autocomplete.addEventListener('click', (e) => {
            const item = e.target.closest('.autocomplete-item');
            if (!item) return;
            locationInput.value = item.dataset.val;
            autocomplete.classList.add('hidden');
            applyFiltersAndSort();
        });
    }

    await fetchAndRender();
});

function navigateToCard(card) {
    const id = card.getAttribute('data-listing-id');
    if (!id) return;
    window.location.href = `/listings/view/${encodeURIComponent(id)}`;
}

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('listings-container');
    if (!container) return;

    container.addEventListener('click', (e) => {
        const card = e.target.closest('.listing-card');
        if (!card) return;
        navigateToCard(card);
    });

    container.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        if (e.target.classList && e.target.classList.contains('listing-carousel-btn')) return;
        const card = e.target.closest('.listing-card');
        if (!card) return;
        e.preventDefault();
        navigateToCard(card);
    });
});
