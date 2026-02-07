/**
 * Location Search Feature
 * Handles beach search autocomplete and location updates
 */

const LocationUpdate = {
    currentLocation: null,
    searchInput: null,
    dropdown: null,
    hiddenInput: null,
    statusDiv: null,
    debounceTimer: null,
    selectedIndex: -1,

    /**
     * Initialize location search handler
     * @param {string} currentLocation - User's current location
     */
    init: function (currentLocation) {
        this.currentLocation = currentLocation;
        this.searchInput = document.getElementById('locationSearch');
        this.dropdown = document.getElementById('locationDropdown');
        this.hiddenInput = document.getElementById('locationValue');
        this.statusDiv = document.getElementById('location-status');

        if (!this.searchInput) {
            console.error('LocationUpdate: Search input not found');
            return;
        }

        this.bindEvents();
    },

    bindEvents: function () {
        const self = this;

        // Input handler with debounce
        this.searchInput.addEventListener('input', function (e) {
            clearTimeout(self.debounceTimer);
            self.debounceTimer = setTimeout(() => {
                self.search(e.target.value);
            }, 200);
        });

        // Focus shows dropdown
        this.searchInput.addEventListener('focus', function () {
            if (this.value.length > 0) {
                self.search(this.value);
            } else {
                self.search(''); // Show all beaches
            }
        });

        // Keyboard navigation
        this.searchInput.addEventListener('keydown', function (e) {
            self.handleKeydown(e);
        });

        // Click outside closes dropdown
        document.addEventListener('click', function (e) {
            if (!self.searchInput.contains(e.target) && !self.dropdown.contains(e.target)) {
                self.hideDropdown();
            }
        });
    },

    async search(query) {
        try {
            const response = await fetch(`/api/beaches/search?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.success) {
                this.renderDropdown(data.beaches);
            }
        } catch (error) {
            console.error('Beach search failed:', error);
        }
    },

    renderDropdown: function (beaches) {
        if (beaches.length === 0) {
            this.dropdown.innerHTML = '<div class="px-4 py-3 text-white/50 text-sm">No beaches found</div>';
        } else {
            this.dropdown.innerHTML = beaches.map((beach, index) => `
                <div class="location-option px-4 py-3 cursor-pointer hover:bg-white/10 transition-colors ${beach.name === this.currentLocation ? 'bg-blue-500/20' : ''}" 
                     data-value="${beach.name}"
                     data-index="${index}">
                    <div class="text-white font-medium">${beach.name}</div>
                    <div class="text-white/40 text-xs">${beach.hebrew_name}</div>
                </div>
            `).join('');

            // Bind click handlers
            const self = this;
            this.dropdown.querySelectorAll('.location-option').forEach(option => {
                option.addEventListener('click', function () {
                    self.selectLocation(this.dataset.value);
                });
            });
        }

        this.selectedIndex = -1;
        this.showDropdown();
    },

    handleKeydown: function (e) {
        const options = this.dropdown.querySelectorAll('.location-option');

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, options.length - 1);
                this.highlightOption(options);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
                this.highlightOption(options);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && options[this.selectedIndex]) {
                    this.selectLocation(options[this.selectedIndex].dataset.value);
                }
                break;
            case 'Escape':
                this.hideDropdown();
                this.searchInput.value = this.currentLocation;
                break;
        }
    },

    highlightOption: function (options) {
        options.forEach((opt, i) => {
            opt.classList.toggle('bg-white/20', i === this.selectedIndex);
        });

        if (options[this.selectedIndex]) {
            options[this.selectedIndex].scrollIntoView({ block: 'nearest' });
        }
    },

    async selectLocation(locationName) {
        if (locationName === this.currentLocation) {
            this.hideDropdown();
            return;
        }

        this.hideDropdown();
        this.searchInput.value = locationName;
        this.searchInput.disabled = true;

        if (this.statusDiv) {
            StatusMessage.loading(this.statusDiv);
        }

        try {
            const result = await ApiClient.post(
                DashboardConfig.API.UPDATE_LOCATION,
                { location: locationName }
            );

            if (result.ok) {
                this.currentLocation = locationName;
                if (this.hiddenInput) {
                    this.hiddenInput.value = locationName;
                }
                if (this.statusDiv) {
                    StatusMessage.success(this.statusDiv, result.data.message);
                }
            } else {
                this.searchInput.value = this.currentLocation;
                if (this.statusDiv) {
                    StatusMessage.error(this.statusDiv, 'Error: ' + result.data.message);
                }
            }
        } catch (error) {
            this.searchInput.value = this.currentLocation;
            if (this.statusDiv) {
                StatusMessage.error(this.statusDiv, 'Failed to update location');
            }
        } finally {
            this.searchInput.disabled = false;
        }
    },

    showDropdown: function () {
        this.dropdown.classList.remove('hidden');
    },

    hideDropdown: function () {
        this.dropdown.classList.add('hidden');
        this.selectedIndex = -1;
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LocationUpdate = LocationUpdate;
}
