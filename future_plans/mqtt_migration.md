# MQTT Migration Plan: From HTTP Polling to Pub/Sub

**Current Status:** HTTP Polling (Pull) + Redis Heartbeats
**Target State:** MQTT Pub/Sub (Push)
**Goal:** Reduce bandwidth cost by ~90% and support >1M concurrent devices.

---

## 🏗️ Phase 1: Infrastructure Setup (The Broker)
*Goal: Establish the central nervous system for messaging.*

1.  **Select Broker:** Use **EMQX** (Open Source) or **VerneMQ**. They are optimized for millions of concurrent connections.
    *   *Avoid Mosquitto for high scale* (single-threaded limitations).
2.  **Deploy to Render:**
    *   Deploy as a Docker Service.
    *   **Ports:** Open `1883` (TCP) and `8883` (SSL/TLS).
    *   *Note:* Render's default load balancer supports WebSockets (`443`). For raw TCP (`1883/8883`), you might need a custom plan or a different provider (DigitalOcean/AWS). **Recommendation: Use MQTT over WebSockets (WSS) on Render.**
3.  **Persistence:** Mount a volume to store persistent sessions/retained messages.

## 🧠 Phase 2: Server-Side Logic (The Publisher)
*Goal: Push updates automatically when the processor finishes.*

1.  **Update `surf-lamp-processor/background_processor.py`:**
    *   Add an MQTT Client.
    *   After `update_location_conditions` succeeds:
        *   Construct the binary payload (V3 protocol).
        *   **Publish** to topic: `surf/updates/{location_id_normalized}`.
        *   *Flag:* `retain=True` (So a lamp connecting *after* the update still gets the latest data immediately).
2.  **Schema Definition:**
    *   Topic: `surf/updates/<location_slug>` (e.g., `surf/updates/tel-aviv-hilton`)
    *   Payload: `[26 bytes binary data]`

## 🔌 Phase 3: Firmware Implementation (The Subscriber)
*Goal: Switch ESP32 from "Ask" to "Listen".*

1.  **Library:** Switch to `PubSubClient` (standard) or `AsyncMqttClient` (better for ESP32).
2.  **Connection Logic:**
    *   Connect to `wss://your-app.onrender.com/mqtt`.
    *   Authenticate (see Phase 4).
    *   **Subscribe** to `surf/updates/{my_location}`.
3.  **Heartbeat Logic:**
    *   **Old:** HTTP Request to `/callback`.
    *   **New:** MQTT PING (Automatic).
    *   *Bonus:* Configure "Last Will & Testament" (LWT). If a lamp dies unexpectedly, the Broker automatically publishes "Offline" to a status topic.
4.  **Fallback:** Keep the HTTP logic! If MQTT fails to connect 3 times, fall back to HTTP polling.

## 🔐 Phase 4: Security & Auth (The Guardian)
*Goal: Prevent unauthorized access and DDoS.*

1.  **Authentication:**
    *   **Strategy:** "Shared Secret" (Simplest) vs. "Unique Certs" (Best).
    *   *Recommendation for Phase 1:* **Dynamic Token Auth**.
    *   Lamp makes 1 HTTP request to `/api/auth/mqtt-token`.
    *   Server verifies identity and returns a short-lived JWT/Token.
    *   Lamp connects to MQTT using this Token as the password.
2.  **Access Control (ACL):**
    *   Configure EMQX ACLs:
        *   Lamps can **SUBSCRIBE** to `surf/updates/+`.
        *   Lamps can **PUBLISH** to `surf/heartbeats`.
        *   Lamps **CANNOT** publish to `surf/updates/+` (prevents spoofing).

## 📊 Comparison: 1 Million Lamps

| Metric | Current (HTTP + Redis) | Future (MQTT Push) |
| :--- | :--- | :--- |
| **Bandwidth (Monthly)** | ~1 TB ($300+) | ~100 GB (<$30) |
| **Latency** | ~15 mins (avg) | < 1 second |
| **Server Load** | 1,000s of req/sec | 0 req/sec (Broker handles it) |
| **Complexity** | Low | High |
| **Cost** | ~$750/mo | ~$300/mo |

---

## 🏁 Migration Checklist
- [ ] Deploy EMQX on Render (or external).
- [ ] Create Python "Publisher" script to test topic structure.
- [ ] Create Arduino "Subscriber" sketch (on a test branch).
- [ ] Implement Token Auth endpoint on Flask.
- [ ] Test 100 concurrent connections.
- [ ] Roll out to "Beta" users (OTA Update).
