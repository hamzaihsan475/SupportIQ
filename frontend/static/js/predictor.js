document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('predict-form');
    const resultDiv = document.getElementById('prediction-result');

    if (!form || !resultDiv) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

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
                resultDiv.innerHTML = `Estimated Price: ${result.predicted_price}`;
                resultDiv.style.background = '#d2ffd2';
            }
        } catch (error) {
            console.error('Error during prediction:', error);
            resultDiv.innerHTML = 'Error connecting to server.';
            resultDiv.style.background = '#ffd2d2';
        }
    });
});