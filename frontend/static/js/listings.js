document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('listings-container');
    if (!container) return;

    try {
        const response = await fetch('/api/listings');
        if (!response.ok) throw new Error('Network response was not ok');

        const listings = await response.json();

        if (listings.length === 0) {
            container.innerHTML = '<p>No listings found.</p>';
            return;
        }

        container.innerHTML = '';
        listings.forEach(listing => {
            const card = document.createElement('div');
            card.className = 'listing-card';
            card.innerHTML = `
                <h3>${listing.address}</h3>
                <p><strong>Price:</strong> ${listing.price}</p>
                <p><strong>Bedrooms:</strong> ${listing.bedrooms} | <strong>Bathrooms:</strong> ${listing.bathrooms}</p>
                <p><strong>Area:</strong> ${listing.area} sq ft</p>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error fetching listings:', error);
        container.innerHTML = '<p>Error loading listings. Please try again later.</p>';
    }
});