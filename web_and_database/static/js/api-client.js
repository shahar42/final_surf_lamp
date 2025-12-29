/**
 * API Client
 * Centralized fetch wrapper with standardized error handling
 */

const ApiClient = {
    /**
     * Make an API request with standardized error handling
     * @param {string} url - API endpoint URL
     * @param {object} options - Fetch options (method, body, etc.)
     * @returns {Promise<{ok: boolean, data: object, status: number}>}
     */
    request: async function(url, options = {}) {
        // Default options
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        };

        // Merge options
        const fetchOptions = { ...defaultOptions, ...options };

        // Convert body to JSON if it's an object
        if (fetchOptions.body && typeof fetchOptions.body === 'object') {
            fetchOptions.body = JSON.stringify(fetchOptions.body);
        }

        try {
            const response = await fetch(url, fetchOptions);

            // Parse JSON response
            let data;
            try {
                data = await response.json();
            } catch (e) {
                // Response not JSON
                data = { message: response.statusText };
            }

            return {
                ok: response.ok,
                status: response.status,
                data: data
            };
        } catch (error) {
            // Network error
            return {
                ok: false,
                status: 0,
                data: {
                    message: 'Network error. Please check your connection and try again.',
                    error: error.message
                }
            };
        }
    },

    /**
     * Convenience method for GET requests
     */
    get: async function(url) {
        return this.request(url, { method: 'GET' });
    },

    /**
     * Convenience method for POST requests
     */
    post: async function(url, body) {
        return this.request(url, {
            method: 'POST',
            body: body
        });
    },

    /**
     * Convenience method for PUT requests
     */
    put: async function(url, body) {
        return this.request(url, {
            method: 'PUT',
            body: body
        });
    },

    /**
     * Convenience method for DELETE requests
     */
    delete: async function(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.ApiClient = ApiClient;
}
