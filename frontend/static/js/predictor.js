document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('predict-form');
    const resultDiv = document.getElementById('prediction-result');
    const addressInput = document.getElementById('address');
    const locationList = document.getElementById('location-suggestions');

    let verifiedLocations = [];

    if (!form || !resultDiv) return;

    // Fetch and populate location suggestions
    try {
        const response = await fetch('/api/locations');
        verifiedLocations = await response.json();

        if (locationList && verifiedLocations.length > 0) {
            locationList.innerHTML = verifiedLocations
                .map(loc => `<option value="${loc}">`)
                .join('');
        }
    } catch (error) {
        console.error('Error fetching locations:', error);
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Strict Validation Guard
        const addressValue = addressInput.value.trim();
        if (!verifiedLocations.includes(addressValue)) {
            alert('Please select a valid location from the verified suggestions dropdown.');
            resultDiv.innerHTML = '';
            resultDiv.style.background = 'transparent';
            return;
        }

        const formData = new FormData(form);
        const data = {
            address: formData.get('address'),
            bedrooms: formData.get('bedrooms'),
            bathrooms: formData.get('bathrooms'),
            area: formData.get('area'),
        };

        resultDiv.innerHTML = 'Predicting...';
        resultDiv.style.background = '#eee';

        try {
            const response = await fetch('/predict-price', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (result.error) {
                resultDiv.innerHTML = `Error: ${result.error}`;
                resultDiv.style.background = '#ffd2d2';
            } else {
                const formattedPrice = Math.round(result.predicted_price).toLocaleString('en-IN');
                resultDiv.innerHTML = `Estimated Price: Rs. ${formattedPrice}`;
                resultDiv.style.background = '#d2ffd2';
            }
        } catch (error) {
            console.error('Error during prediction:', error);
            resultDiv.innerHTML = 'Error connecting to server.';
            resultDiv.style.background = '#ffd2d2';
        }
    });
});
