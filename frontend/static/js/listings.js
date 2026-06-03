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
            card.className = 'listing-card';
            card.innerHTML = `
                <h3 class="listing-title">${listing.title || listing.address || 'Unnamed Property'}</h3>
                <p><strong class="label">Location:</strong> ${listing.location || listing.address || 'N/A'}</p>
                <p><strong class="label">Type:</strong> ${listing.property_type || 'N/A'}</p>
                <p><strong class="label">Area:</strong> ${listing.area || 'N/A'} sq yards</p>
                <p><strong class="label">Rooms:</strong> ${listing.bedrooms || 0} Bed | ${listing.bathrooms || 0} Bath</p>
                <p class="listing-price"><strong class="label">Price:</strong> ${formatPKR(listing.price)}</p>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error fetching listings:', error);
        container.innerHTML = '<p>Error loading listings. Please try again later.</p>';
    }
});
