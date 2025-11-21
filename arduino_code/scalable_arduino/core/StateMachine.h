#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <Arduino.h>

/**
 * State Machine for ESP32 System Flow
 * - Manages WiFi connection states
 * - Clean state transitions
 * - Event-driven state changes
 * - Professional pattern: FSM (Finite State Machine)
 */

// System States
enum SystemState {
    STATE_INIT = 0,              // Initial boot state
    STATE_WIFI_CONNECTING,       // Attempting to connect to WiFi
    STATE_WIFI_CONFIG_AP,        // AP mode for WiFi configuration
    STATE_OPERATIONAL,           // Normal operation with WiFi connected
    STATE_WIFI_RECONNECTING,     // Recovering from WiFi disconnection
    STATE_ERROR                  // Error state
};

// State Transition Events
enum StateEvent {
    EVENT_BOOT_COMPLETE = 0,
    EVENT_WIFI_CONNECT_SUCCESS,
    EVENT_WIFI_CONNECT_FAILED,
    EVENT_CONFIG_MODE_ENTERED,
    EVENT_CONFIG_COMPLETE,
    EVENT_WIFI_DISCONNECTED,
    EVENT_ERROR_OCCURRED,
    EVENT_NONE
};

class StateMachine {
private:
    SystemState currentState;
    SystemState previousState;
    unsigned long stateStartTime;
    unsigned long lastStateChange;

    // State callbacks (function pointers)
    void (*onEnterState)(SystemState);
    void (*onExitState)(SystemState);
    void (*onStateUpdate)(SystemState, unsigned long);  // Called periodically in current state

public:
    StateMachine()
        : currentState(STATE_INIT)
        , previousState(STATE_INIT)
        , stateStartTime(0)
        , lastStateChange(0)
        , onEnterState(nullptr)
        , onExitState(nullptr)
        , onStateUpdate(nullptr)
    {
        stateStartTime = millis();
    }

    /**
     * Get current state
     */
    SystemState getState() const {
        return currentState;
    }

    /**
     * Get previous state
     */
    SystemState getPreviousState() const {
        return previousState;
    }

    /**
     * Get time elapsed in current state (milliseconds)
     */
    unsigned long getTimeInState() const {
        return millis() - stateStartTime;
    }

    /**
     * Get time since last state change
     */
    unsigned long getTimeSinceStateChange() const {
        return millis() - lastStateChange;
    }

    /**
     * Check if in a specific state
     */
    bool isInState(SystemState state) const {
        return currentState == state;
    }

    /**
     * Transition to a new state
     * @param newState Target state
     * @param event Event triggering the transition (for logging)
     */
    void transitionTo(SystemState newState, StateEvent event = EVENT_NONE) {
        if (newState == currentState) {
            Serial.println("⚠️ StateMachine: Attempted transition to same state");
            return;
        }

        // Log transition
        Serial.printf("🔄 StateMachine: %s → %s",
                      stateToString(currentState),
                      stateToString(newState));

        if (event != EVENT_NONE) {
            Serial.printf(" (Event: %s)", eventToString(event));
        }
        Serial.println();

        // Call exit callback for current state
        if (onExitState != nullptr) {
            onExitState(currentState);
        }

        // Update state
        previousState = currentState;
        currentState = newState;
        stateStartTime = millis();
        lastStateChange = millis();

        // Call enter callback for new state
        if (onEnterState != nullptr) {
            onEnterState(newState);
        }
    }

    /**
     * Process an event (may trigger state transition)
     * @param event Event to process
     * @return true if state changed, false otherwise
     */
    bool processEvent(StateEvent event) {
        SystemState oldState = currentState;

        Serial.printf("📨 StateMachine: Processing event %s in state %s\n",
                      eventToString(event),
                      stateToString(currentState));

        // State transition logic
        switch (currentState) {
            case STATE_INIT:
                if (event == EVENT_BOOT_COMPLETE) {
                    transitionTo(STATE_WIFI_CONNECTING, event);
                }
                break;

            case STATE_WIFI_CONNECTING:
                if (event == EVENT_WIFI_CONNECT_SUCCESS) {
                    transitionTo(STATE_OPERATIONAL, event);
                } else if (event == EVENT_WIFI_CONNECT_FAILED) {
                    transitionTo(STATE_WIFI_CONFIG_AP, event);
                }
                break;

            case STATE_WIFI_CONFIG_AP:
                if (event == EVENT_CONFIG_COMPLETE) {
                    transitionTo(STATE_WIFI_CONNECTING, event);
                } else if (event == EVENT_WIFI_CONNECT_SUCCESS) {
                    transitionTo(STATE_OPERATIONAL, event);
                }
                break;

            case STATE_OPERATIONAL:
                if (event == EVENT_WIFI_DISCONNECTED) {
                    transitionTo(STATE_WIFI_RECONNECTING, event);
                } else if (event == EVENT_ERROR_OCCURRED) {
                    transitionTo(STATE_ERROR, event);
                }
                break;

            case STATE_WIFI_RECONNECTING:
                if (event == EVENT_WIFI_CONNECT_SUCCESS) {
                    transitionTo(STATE_OPERATIONAL, event);
                } else if (event == EVENT_WIFI_CONNECT_FAILED) {
                    transitionTo(STATE_WIFI_CONFIG_AP, event);
                }
                break;

            case STATE_ERROR:
                // Can only exit error state by explicit transition
                Serial.println("⚠️ StateMachine: In error state, manual recovery required");
                break;
        }

        return oldState != currentState;
    }

    /**
     * Update function - call this in loop()
     * Calls onStateUpdate callback if set
     */
    void update() {
        if (onStateUpdate != nullptr) {
            onStateUpdate(currentState, getTimeInState());
        }
    }

    /**
     * Register callback for state entry
     * @param callback Function to call when entering a state
     */
    void setOnEnterState(void (*callback)(SystemState)) {
        onEnterState = callback;
    }

    /**
     * Register callback for state exit
     * @param callback Function to call when exiting a state
     */
    void setOnExitState(void (*callback)(SystemState)) {
        onExitState = callback;
    }

    /**
     * Register callback for state update (called in loop)
     * @param callback Function to call on each update
     */
    void setOnStateUpdate(void (*callback)(SystemState, unsigned long)) {
        onStateUpdate = callback;
    }

    /**
     * Force a state (for testing/recovery)
     * @param newState State to force
     */
    void forceState(SystemState newState) {
        Serial.printf("⚠️ StateMachine: FORCE transition %s → %s\n",
                      stateToString(currentState),
                      stateToString(newState));

        previousState = currentState;
        currentState = newState;
        stateStartTime = millis();
        lastStateChange = millis();
    }

    /**
     * Print current state status
     */
    void printStatus() const {
        Serial.println("📊 StateMachine Status:");
        Serial.printf("   Current State: %s\n", stateToString(currentState));
        Serial.printf("   Previous State: %s\n", stateToString(previousState));
        Serial.printf("   Time in State: %lu ms\n", getTimeInState());
        Serial.printf("   Time Since Change: %lu ms\n", getTimeSinceStateChange());
    }

    /**
     * Convert state enum to string
     */
    const char* stateToString(SystemState state) const {
        switch (state) {
            case STATE_INIT:              return "INIT";
            case STATE_WIFI_CONNECTING:   return "WIFI_CONNECTING";
            case STATE_WIFI_CONFIG_AP:    return "WIFI_CONFIG_AP";
            case STATE_OPERATIONAL:       return "OPERATIONAL";
            case STATE_WIFI_RECONNECTING: return "WIFI_RECONNECTING";
            case STATE_ERROR:             return "ERROR";
            default:                      return "UNKNOWN";
        }
    }

    /**
     * Convert event enum to string
     */
    const char* eventToString(StateEvent event) const {
        switch (event) {
            case EVENT_BOOT_COMPLETE:        return "BOOT_COMPLETE";
            case EVENT_WIFI_CONNECT_SUCCESS: return "WIFI_CONNECT_SUCCESS";
            case EVENT_WIFI_CONNECT_FAILED:  return "WIFI_CONNECT_FAILED";
            case EVENT_CONFIG_MODE_ENTERED:  return "CONFIG_MODE_ENTERED";
            case EVENT_CONFIG_COMPLETE:      return "CONFIG_COMPLETE";
            case EVENT_WIFI_DISCONNECTED:    return "WIFI_DISCONNECTED";
            case EVENT_ERROR_OCCURRED:       return "ERROR_OCCURRED";
            case EVENT_NONE:                 return "NONE";
            default:                         return "UNKNOWN";
        }
    }
};

#endif // STATE_MACHINE_H
