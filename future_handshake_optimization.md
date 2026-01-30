# Future Handshake Optimization: TLS Session Resumption

## Overview
This document outlines the plan to implement TLS Session Resumption on the Surf Lamp (ESP32) to reduce network overhead and connection latency.

## Current Problem
Every time the lamp connects to the API (approx. every 13 minutes), it performs a full TLS handshake.
- **Data Cost:** ~3,500 - 5,000 bytes per connection (mostly the certificate chain).
- **Time Cost:** 1-3 seconds depending on network conditions.
- **Scaling Limit:** High overhead limits the number of lamps a single basic server/bandwidth plan can support.

## Proposed Solution: Session Resumption
Use the TLS "Session Ticket" mechanism to allow the ESP32 and the server to remember the previous security context.

### 1. Technical Implementation
Since the standard `WiFiClientSecure` library does not expose session management, we will create a subclass to access the underlying mbedTLS context.

#### Subclass Strategy (`ResumableClient`):
- Inherit from `WiFiClientSecure`.
- Access the `protected` member `sslclient`.
- Use the following mbedTLS functions:
    - `mbedtls_ssl_get_session()`: Save the session ticket after a successful handshake.
    - `mbedtls_ssl_set_session()`: Restore the ticket before calling `connect()`.

### 2. Persistence Strategy
- **Current (Wall Powered):** Store the session ticket in a global `mbedtls_ssl_session` struct within the `ResumableClient` instance.
- **Future (Deep Sleep):** Store the session ticket in **RTC FAST RAM** using the `RTC_NOINIT_ATTR` attribute. This allows the session to survive even if the main CPU is powered down between updates.

### 3. Integration Plan
1.  **Create `ResumableClient.h`**: A header-only wrapper for the customized SSL logic.
2.  **Update `WebServerHandler`**: Replace the global `WiFiClientSecure globalHttpsClient` with `ResumableClient globalHttpsClient`.
3.  **Modify `fetchSurfDataFromServer()`**:
    - Call `globalHttpsClient.saveSession()` after successful `http.GET()`.
    - Ensure `http.begin()` uses the resumable client.

## Expected Results
- **Handshake Size:** Reduced from ~4,000 bytes to **~300 bytes** (92% reduction in overhead).
- **Connection Speed:** Handshake time reduced from ~1.5s to **<200ms**.
- **Server Capacity:** Increased by approx. 5x - 10x on the same bandwidth budget.

## Status
- **Investigation:** COMPLETED. (mbedTLS headers and protected access confirmed).
- **Implementation:** PENDING (Awaiting developer instruction).
