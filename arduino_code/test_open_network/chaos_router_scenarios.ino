/*
 * ROUTER CHAOS MODE - WiFi Edge Case Simulator
 *
 * Purpose: Simulate problematic router behaviors to test lamp's WiFi resilience
 *
 * Test Scenarios:
 * 1. Open network with frequent disconnects
 * 2. DHCP delays (slow router)
 * 3. Connected but no internet
 * 4. Random router reboots
 * 5. Short DHCP leases (forces frequent renewal)
 *
 * Usage: Upload to ESP32, select scenario via serial commands
 */

#include <WiFi.h>
#include <WiFiClient.h>
#include <DNSServer.h>

// Configuration
#define AP_SSID "TestOpenNetwork"
#define CHAOS_MODE_ENABLED true

// Test scenario selection
enum ChaosScenario {
  STABLE_OPEN,              // Baseline: Normal open network
  FREQUENT_DISCONNECTS,     // Disconnect every 30 seconds
  DHCP_DELAYS,              // Slow DHCP responses
  RANDOM_REBOOTS,           // AP restarts randomly
  NO_INTERNET,              // Connected but no internet (common customer complaint)
  SHORT_LEASES              // Force frequent DHCP renewal
};

ChaosScenario currentScenario = STABLE_OPEN;

// Chaos timing
unsigned long lastChaosEvent = 0;
const unsigned long DISCONNECT_INTERVAL = 30000;  // 30 seconds
const unsigned long REBOOT_INTERVAL = 120000;     // 2 minutes

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n================================");
  Serial.println("ROUTER CHAOS MODE - WiFi Tester");
  Serial.println("================================\n");

  printMenu();
  startAP(currentScenario);
}

void loop() {
  static int lastClientCount = -1;
  int clientCount = WiFi.softAPgetStationNum();

  // Monitor client connections
  if (clientCount != lastClientCount) {
    Serial.printf("[%lu ms] Connected clients: %d\n", millis(), clientCount);
    if (clientCount > lastClientCount) {
      Serial.println("  ✅ LAMP CONNECTED");
      logClientInfo();
    } else {
      Serial.println("  ❌ LAMP DISCONNECTED");
    }
    lastClientCount = clientCount;
  }

  // Execute chaos scenarios
  if (CHAOS_MODE_ENABLED && clientCount > 0) {
    executeChaosScenario();
  }

  // Handle serial commands
  if (Serial.available()) {
    handleSerialCommand();
  }

  delay(500);
}

void printMenu() {
  Serial.println("Select Test Scenario:");
  Serial.println("  0 - STABLE_OPEN (normal open network)");
  Serial.println("  1 - FREQUENT_DISCONNECTS (drop every 30s)");
  Serial.println("  2 - DHCP_DELAYS (slow responses)");
  Serial.println("  3 - RANDOM_REBOOTS (restart every 2min)");
  Serial.println("  4 - NO_INTERNET (connected but blocked)");
  Serial.println("  5 - SHORT_LEASES (force frequent renewal)");
  Serial.println("\nType scenario number and press Enter\n");
}

void handleSerialCommand() {
  char cmd = Serial.read();

  if (cmd >= '0' && cmd <= '5') {
    currentScenario = (ChaosScenario)(cmd - '0');
    Serial.printf("\n✅ Switched to scenario %d\n", currentScenario);
    Serial.println("Restarting AP with new scenario...\n");
    WiFi.softAPdisconnect(true);
    delay(1000);
    startAP(currentScenario);
    lastChaosEvent = millis();
  } else {
    printMenu();
  }

  // Clear serial buffer
  while (Serial.available()) Serial.read();
}

void startAP(ChaosScenario scenario) {
  Serial.printf("Starting AP: %s\n", AP_SSID);
  Serial.printf("Scenario: %d ", scenario);

  switch(scenario) {
    case STABLE_OPEN:
      Serial.println("(STABLE - Normal open network)");
      WiFi.softAP(AP_SSID);
      break;

    case FREQUENT_DISCONNECTS:
      Serial.println("(CHAOS - Disconnect every 30s)");
      WiFi.softAP(AP_SSID);
      break;

    case DHCP_DELAYS:
      Serial.println("(CHAOS - Slow DHCP)");
      WiFi.softAP(AP_SSID);
      Serial.println("⚠️ DHCP delay simulation not fully implemented");
      break;

    case RANDOM_REBOOTS:
      Serial.println("(CHAOS - Random reboots every 2min)");
      WiFi.softAP(AP_SSID);
      break;

    case NO_INTERNET:
      Serial.println("(CHAOS - No internet gateway)");
      WiFi.softAP(AP_SSID);
      // Don't configure gateway route
      break;

    case SHORT_LEASES:
      Serial.println("(CHAOS - Short DHCP leases)");
      WiFi.softAP(AP_SSID);
      Serial.println("⚠️ Short lease simulation requires custom DHCP server");
      break;
  }

  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());
  Serial.println("Waiting for lamp connection...\n");
}

void executeChaosScenario() {
  unsigned long now = millis();

  switch(currentScenario) {
    case FREQUENT_DISCONNECTS:
      if (now - lastChaosEvent >= DISCONNECT_INTERVAL) {
        Serial.println("\n🔥 CHAOS EVENT: Forcing disconnect!");
        WiFi.softAPdisconnect(false); // Don't turn off WiFi
        delay(100);
        WiFi.softAP(AP_SSID); // Restart AP
        lastChaosEvent = now;
      }
      break;

    case RANDOM_REBOOTS:
      if (now - lastChaosEvent >= REBOOT_INTERVAL) {
        Serial.println("\n🔥 CHAOS EVENT: Simulating router reboot!");
        WiFi.softAPdisconnect(true);
        delay(5000); // Simulate boot time
        WiFi.softAP(AP_SSID);
        Serial.println("Router back online");
        lastChaosEvent = now;
      }
      break;

    default:
      // Stable or not implemented
      break;
  }
}

void logClientInfo() {
  wifi_sta_list_t stationList;
  esp_wifi_ap_get_sta_list(&stationList);

  Serial.println("  Client Details:");
  for (int i = 0; i < stationList.num; i++) {
    Serial.printf("    MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                  stationList.sta[i].mac[0],
                  stationList.sta[i].mac[1],
                  stationList.sta[i].mac[2],
                  stationList.sta[i].mac[3],
                  stationList.sta[i].mac[4],
                  stationList.sta[i].mac[5]);
  }
}
