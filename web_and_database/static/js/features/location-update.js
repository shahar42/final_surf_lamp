/**
 * Location Search Feature - Premium Autocomplete
 * 
 * Design principles:
 * - Dropdown feels attached, not floating
 * - Clear information hierarchy
 * - Smooth hover/keyboard navigation
 * - Loading and empty states
 */

const LocationUpdate = {
    currentLocation: null,
    searchInput: null,
    dropdown: null,
    container: null,
    hiddenInput: null,
    statusDiv: null,
    debounceTimer: null,
    selectedIndex: -1,
    isLoading: false,
    beaches: [],

    /**
     * Initialize location search handler
     * @param {string} currentLocation - User's current location
     */
    init: function (currentLocation) {
        this.currentLocation = currentLocation;
        this.searchInput = document.getElementById('locationSearch');
        this.dropdown = document.getElementById('locationDropdown');
        this.container = document.getElementById('locationSearchContainer');
        this.hiddenInput = document.getElementById('locationValue');
        this.statusDiv = document.getElementById('location-status');

        if (!this.searchInput || !this.dropdown) {
            console.error('LocationUpdate: Required elements not found');
            return;
        }

        this.bindEvents();
    },

    bindEvents: function () {
        const self = this;

        // Input handler with debounce
        this.searchInput.addEventListener('input', function (e) {
            clearTimeout(self.debounceTimer);
            self.showLoading();
            self.debounceTimer = setTimeout(() => {
                self.search(e.target.value);
            }, 200);
        });

        // Focus shows dropdown
        this.searchInput.addEventListener('focus', function () {
            self.showLoading();
            self.search(this.value || '');
        });

        // Keyboard navigation
        this.searchInput.addEventListener('keydown', function (e) {
            self.handleKeydown(e);
        });

        // Click outside closes dropdown
        document.addEventListener('click', function (e) {
            if (!self.container?.contains(e.target)) {
                self.hideDropdown();
            }
        });
    },

    showLoading: function () {
        this.isLoading = true;
        this.dropdown.innerHTML = `
            <div class="location-skeleton">
                <div class="location-skeleton-line primary"></div>
                <div class="location-skeleton-line secondary"></div>
            </div>
            <div class="location-skeleton">
                <div class="location-skeleton-line primary"></div>
                <div class="location-skeleton-line secondary"></div>
            </div>
            <div class="location-skeleton">
                <div class="location-skeleton-line primary"></div>
                <div class="location-skeleton-line secondary"></div>
            </div>
        `;
        this.showDropdown();
    },

    async search(query) {
        try {
            const response = await fetch(`/api/beaches/search?q=${encodeURIComponent(query)}&limit=8`);
            const data = await response.json();

            this.isLoading = false;

            if (data.success) {
                this.beaches = data.beaches;
                this.renderDropdown(data.beaches);
            }
        } catch (error) {
            console.error('Beach search failed:', error);
            this.isLoading = false;
            this.renderEmpty('Search unavailable');
        }
    },

    renderDropdown: function (beaches) {
        if (beaches.length === 0) {
            this.renderEmpty('No beaches found');
            return;
        }

        this.dropdown.innerHTML = beaches.map((beach, index) => {
            const isCurrent = beach.name === this.currentLocation;
            // Use explicit region metadata instead of parsing from name
            const displayName = beach.name.replace(/\s*\([^)]*\)/, '');
            const region = beach.region || 'Israel';

            return `
                <div class="location-option ${isCurrent ? 'current' : ''}"
                     data-value="${beach.name}"
                     data-index="${index}">
                    <div class="location-option-primary">${displayName}</div>
                    <div class="location-option-secondary">${region} · ${beach.hebrew_name}</div>
                </div>
            `;
        }).join('');

        // Bind click handlers
        const self = this;
        this.dropdown.querySelectorAll('.location-option').forEach(option => {
            option.addEventListener('click', function () {
                self.selectLocation(this.dataset.value);
            });

            option.addEventListener('mouseenter', function () {
                self.selectedIndex = parseInt(this.dataset.index);
                self.updateHighlight();
            });
        });

        this.selectedIndex = -1;
        this.showDropdown();
    },

    renderEmpty: function (message) {
        this.dropdown.innerHTML = `
            <div class="location-empty-state">
                <div class="location-empty-state-icon">🏖️</div>
                <div class="location-empty-state-text">${message}</div>
            </div>
        `;
        this.showDropdown();
    },

    handleKeydown: function (e) {
        const options = this.dropdown.querySelectorAll('.location-option');

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, options.length - 1);
                this.updateHighlight();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
                this.updateHighlight();
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
                this.searchInput.blur();
                break;
            case 'Tab':
                this.hideDropdown();
                break;
        }
    },

    updateHighlight: function () {
        const options = this.dropdown.querySelectorAll('.location-option');

        options.forEach((opt, i) => {
            opt.classList.toggle('highlighted', i === this.selectedIndex);
        });

        if (options[this.selectedIndex]) {
            options[this.selectedIndex].scrollIntoView({
                block: 'nearest',
                behavior: 'smooth'
            });
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
        this.dropdown.classList.add('visible');
        this.container?.classList.add('dropdown-open');
    },

    hideDropdown: function () {
        this.dropdown.classList.remove('visible');
        this.container?.classList.remove('dropdown-open');
        this.selectedIndex = -1;
    }
};

// Make globally available
if (typeof window !== 'undefined') {
    window.LocationUpdate = LocationUpdate;
}
