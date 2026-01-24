const Notifications = {
    publicKey: null,
    swRegistration: null,
    isSubscribed: false,

    init: async function() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            console.log('Push notifications not supported');
            const toggle = document.getElementById('notificationToggle');
            if (toggle) toggle.classList.add('hidden');
            return;
        }

        try {
            // Register SW
            this.swRegistration = await navigator.serviceWorker.register('/sw.js');
            console.log('SW Registered');

            // Fetch Key (with cache busting)
            const response = await fetch('/notifications/vapid-public-key?t=' + Date.now());
            if (!response.ok) throw new Error('Failed to fetch VAPID key');
            const data = await response.json();
            this.publicKey = data.publicKey;

            // Check current subscription
            await this.updateSubscriptionStatus();

            // Bind UI
            const toggle = document.getElementById('notificationToggle');
            if (toggle) {
                toggle.addEventListener('click', () => {
                    this.toggleSubscription();
                });
            }

        } catch (error) {
            console.error('Notification init failed:', error);
        }
    },

    urlB64ToUint8Array: function(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    },

    updateSubscriptionStatus: async function() {
        const subscription = await this.swRegistration.pushManager.getSubscription();
        this.isSubscribed = !!subscription;
        this.updateUI();
    },

    updateUI: function() {
        const bellOutline = document.getElementById('bellOutline');
        const bellSolid = document.getElementById('bellSolid');
        const toggle = document.getElementById('notificationToggle');
        
        if (!toggle || !bellOutline || !bellSolid) return;

        if (this.isSubscribed) {
            bellOutline.classList.add('hidden');
            bellSolid.classList.remove('hidden');
            toggle.classList.add('text-yellow-400');
            toggle.classList.remove('text-white/80');
        } else {
            bellOutline.classList.remove('hidden');
            bellSolid.classList.add('hidden');
            toggle.classList.remove('text-yellow-400');
            toggle.classList.add('text-white/80');
        }
    },

    toggleSubscription: async function() {
        if (this.isSubscribed) {
            // Unsubscribe logic (optional for now, but good UX)
             // For now, we only support subscribing or re-subscribing.
             // Real unsubscribe requires server call to delete.
             // Let's just do browser unsubscribe for now.
             
             // However, typically users click to toggle.
            const subscription = await this.swRegistration.pushManager.getSubscription();
            if (subscription) {
                await subscription.unsubscribe();
                this.isSubscribed = false;
                this.updateUI();
                // TODO: Call backend to remove subscription
            }
        } else {
            // Subscribe
            try {
                const applicationServerKey = this.urlB64ToUint8Array(this.publicKey);
                const subscription = await this.swRegistration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: applicationServerKey
                });

                // Send to backend
                await fetch('/notifications/subscribe', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(subscription)
                });

                this.isSubscribed = true;
                this.updateUI();
                alert('Notifications enabled! You will receive alerts for surf conditions.');
                
            } catch (err) {
                console.error('Failed to subscribe:', err);
                // Check if denied
                if (Notification.permission === 'denied') {
                     alert('Notifications are blocked. Please reset permissions in your browser settings.');
                } else {
                     alert('Could not enable notifications. Error: ' + err.message);
                }
            }
        }
    }
};
