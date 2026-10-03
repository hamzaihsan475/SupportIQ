/**
 * UI State Manager
 * Provides consistent loading, empty, and error states across the application.
 */
const UIState = {
    showLoading: (container) => {
        container.innerHTML = `
            <div class="state-container loading">
                <div class="spinner"></div>
                <p>Loading...</p>
            </div>
        `;
    },
    showEmpty: (container, message = "No results found", actionText = null, actionFn = null) => {
        const actionBtn = actionFn ?
            `<button class="btn btn-secondary" id="state-action-btn">${actionText}</button>` : '';

        container.innerHTML = `
            <div class="state-container empty">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--color-border); margin-bottom: 1rem;">
                    <path d="m21 21-4.3-4.3"/><circle cx="10" cy="10" r="7"/>
                </svg>
                <h3>${message}</h3>
                ${actionBtn}
            </div>
        `;
        if (actionFn) {
            document.getElementById('state-action-btn').onclick = actionFn;
        }
    },
    showError: (container, error = "An unexpected error occurred", retryFn = null) => {
        const retryBtn = retryFn ?
            `<button class="btn btn-primary" id="state-retry-btn">Try Again</button>` : '';

        container.innerHTML = `
            <div class="state-container error">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--color-accent); margin-bottom: 1rem;">
                    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <h3>Oops!</h3>
                <p>${error}</p>
                ${retryBtn}
            </div>
        `;
        if (retryFn) {
            document.getElementById('state-retry-btn').onclick = retryFn;
        }
    }
};
