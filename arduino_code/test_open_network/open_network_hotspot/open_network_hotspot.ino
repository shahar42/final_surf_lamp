/*
 * OPEN NETWORK HOTSPOT - Test Tool
 *
 * Purpose: Create a passwordless WiFi network to test lamp connection
 *          to open networks and capture serial logs.
 *
 * Hardware: Any ESP32 or ESP8266
 *
 * Upload this code, then try connecting your surf lamp to the
 * "TestOpenNetwork" SSID (no password).
 *
 * Watch BOTH serial monitors:
 * - This hotspot: Shows when lamp connects
 * - Surf lamp: Shows connection attempt logs
 */

#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n================================");
  Serial.println("OPEN NETWORK HOTSPOT TEST");
  Serial.println("================================\n");

  // Create open network (no password = open)
  Serial.println("Creating open WiFi network...");
  bool success = WiFi.softAP("TestOpenNetwork");

  if (success) {
    Serial.println("✅ Hotspot created successfully!");
    Serial.println("\nNetwork Details:");
    Serial.println("  SSID: TestOpenNetwork");
    Serial.println("  Password: NONE (open network)");
    Serial.print("  IP Address: ");
    Serial.println(WiFi.softAPIP());
    Serial.println("\n================================");
    Serial.println("Waiting for lamp to connect...");
    Serial.println("================================\n");
  } else {
    Serial.println("❌ Failed to create hotspot!");
    Serial.println("Check if WiFi is already in use");
  }
}

void loop() {
  static int lastClientCount = -1;
  static unsigned long lastPrintTime = 0;
  unsigned long now = millis();

  // Check connected clients
  int clientCount = WiFi.softAPgetStationNum();

  // Print when client count changes
  if (clientCount != lastClientCount) {
    Serial.printf("[%lu ms] Connected clients: %d\n", now, clientCount);

    if (clientCount > lastClientCount) {
      Serial.println("  ✅ NEW DEVICE CONNECTED!");
    } else if (clientCount < lastClientCount) {
      Serial.println("  ❌ DEVICE DISCONNECTED");
    }

    lastClientCount = clientCount;
  }

  // Periodic heartbeat (every 10 seconds)
  if (now - lastPrintTime > 10000) {
    Serial.printf("[%lu ms] Heartbeat - %d client(s) connected\n", now, clientCount);
    lastPrintTime = now;
  }

  delay(500);
}
