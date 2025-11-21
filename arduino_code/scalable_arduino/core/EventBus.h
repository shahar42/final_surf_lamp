#ifndef EVENT_BUS_H
#define EVENT_BUS_H

#include <Arduino.h>

/**
 * Lightweight Event Bus for ESP32
 * - Memory-safe: Fixed array allocation (no dynamic memory)
 * - Event-driven: Decouples modules via publish/subscribe
 * - Professional pattern: Observer pattern implementation
 */

// Event Types
enum EventType {
    EVENT_DATA_RECEIVED = 0,
    EVENT_WIFI_CONNECTED,
    EVENT_WIFI_DISCONNECTED,
    EVENT_THRESHOLD_EXCEEDED,
    EVENT_QUIET_HOURS_CHANGED,
    EVENT_THEME_CHANGED,
    EVENT_CONFIG_CHANGED,
    EVENT_ERROR,
    EVENT_TYPE_COUNT  // Used for validation
};

// Event Data Structure (flexible payload)
struct Event {
    EventType type;
    void* data;         // Pointer to event-specific data
    uint32_t timestamp; // When event occurred
};

// Subscription Structure
struct Subscription {
    EventType type;
    void (*callback)(const Event&);  // Function pointer to handler
    bool active;  // Is this subscription slot in use?
};

class EventBus {
private:
    static const uint8_t MAX_SUBSCRIPTIONS = 20;  // Adjust based on needs
    Subscription subscriptions[MAX_SUBSCRIPTIONS];
    uint8_t subscriptionCount;

    // Event queue for async processing (optional)
    static const uint8_t QUEUE_SIZE = 10;
    Event eventQueue[QUEUE_SIZE];
    uint8_t queueHead;
    uint8_t queueTail;

public:
    EventBus() : subscriptionCount(0), queueHead(0), queueTail(0) {
        // Initialize all subscriptions as inactive
        for (uint8_t i = 0; i < MAX_SUBSCRIPTIONS; i++) {
            subscriptions[i].active = false;
        }
    }

    /**
     * Subscribe to an event type
     * @param type Event type to listen for
     * @param callback Function to call when event occurs
     * @return true if subscription successful, false if no slots available
     */
    bool subscribe(EventType type, void (*callback)(const Event&)) {
        if (subscriptionCount >= MAX_SUBSCRIPTIONS) {
            Serial.println("⚠️ EventBus: Max subscriptions reached!");
            return false;
        }

        // Find first inactive slot
        for (uint8_t i = 0; i < MAX_SUBSCRIPTIONS; i++) {
            if (!subscriptions[i].active) {
                subscriptions[i].type = type;
                subscriptions[i].callback = callback;
                subscriptions[i].active = true;
                subscriptionCount++;

                Serial.printf("✅ EventBus: Subscribed to event %d (slot %d)\n", type, i);
                return true;
            }
        }

        return false;
    }

    /**
     * Publish an event immediately (synchronous)
     * Calls all subscribers for this event type
     */
    void publish(EventType type, void* data = nullptr) {
        Event event;
        event.type = type;
        event.data = data;
        event.timestamp = millis();

        Serial.printf("📢 EventBus: Publishing event %d\n", type);

        // Call all matching subscribers
        uint8_t handlerCount = 0;
        for (uint8_t i = 0; i < MAX_SUBSCRIPTIONS; i++) {
            if (subscriptions[i].active && subscriptions[i].type == type) {
                subscriptions[i].callback(event);
                handlerCount++;
            }
        }

        Serial.printf("   Notified %d handlers\n", handlerCount);
    }

    /**
     * Queue an event for async processing (process later in loop)
     * Useful for events that arrive during interrupt handlers
     */
    bool queueEvent(EventType type, void* data = nullptr) {
        uint8_t nextTail = (queueTail + 1) % QUEUE_SIZE;

        if (nextTail == queueHead) {
            Serial.println("⚠️ EventBus: Queue full, dropping event!");
            return false;
        }

        eventQueue[queueTail].type = type;
        eventQueue[queueTail].data = data;
        eventQueue[queueTail].timestamp = millis();

        queueTail = nextTail;
        return true;
    }

    /**
     * Process queued events (call this in loop())
     * Processes all queued events in FIFO order
     */
    void processQueue() {
        while (queueHead != queueTail) {
            Event& event = eventQueue[queueHead];

            // Publish queued event
            publish(event.type, event.data);

            // Move to next event
            queueHead = (queueHead + 1) % QUEUE_SIZE;
        }
    }

    /**
     * Unsubscribe from an event
     * @param callback The callback function to remove
     * @return true if unsubscribed, false if not found
     */
    bool unsubscribe(void (*callback)(const Event&)) {
        for (uint8_t i = 0; i < MAX_SUBSCRIPTIONS; i++) {
            if (subscriptions[i].active && subscriptions[i].callback == callback) {
                subscriptions[i].active = false;
                subscriptionCount--;
                Serial.printf("🔕 EventBus: Unsubscribed from slot %d\n", i);
                return true;
            }
        }
        return false;
    }

    /**
     * Get subscription count (for debugging)
     */
    uint8_t getSubscriptionCount() const {
        return subscriptionCount;
    }

    /**
     * Clear all subscriptions (for testing/reset)
     */
    void clear() {
        for (uint8_t i = 0; i < MAX_SUBSCRIPTIONS; i++) {
            subscriptions[i].active = false;
        }
        subscriptionCount = 0;
        queueHead = 0;
        queueTail = 0;
        Serial.println("🧹 EventBus: All subscriptions cleared");
    }
};

#endif // EVENT_BUS_H
