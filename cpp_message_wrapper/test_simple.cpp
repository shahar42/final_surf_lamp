#include <iostream>
#include <vector>
#include "include/message_wrapper.h"

int main() {
    std::cout << "Testing Message Wrapper\n";
    std::cout << "=======================\n\n";

    MessageHandler handler;

    // Test 1: Create a valid test message
    std::cout << "Test 1: Creating test message...\n";

    // Use existing SurfData and SettingsData constructors
    uint64_t surf_packed = SurfData::PackData(
        12,     // wave_period_s
        150,    // wave_height_cm
        100,    // wave_threshold_cm
        25,     // wind_speed_mps
        20,     // wind_threshold_knots
        180,    // wind_direction_deg
        false,  // stale_data
        true,   // data_available
        false,  // quiet_hours
        false   // off_hours
    );

    SurfData surf(surf_packed);
    uint8_t surf_crc = surf.CalculateCRC();

    std::cout << "  ✓ SurfData created\n";
    std::cout << "    - Wave height: " << (int)surf.GetWaveHeight() << " cm\n";
    std::cout << "    - Wave period: " << (int)surf.GetWavePeriod() << " s\n";
    std::cout << "    - Wind speed: " << (int)surf.GetWindSpeed() << " m/s\n";
    std::cout << "    - CRC: 0x" << std::hex << (int)surf_crc << std::dec << "\n";

    // Settings data
    uint64_t settings_data1, settings_data2;
    SettingsData::Pack(
        LEDTheme::CLASSIC_SURF,
        80,         // brightness
        300000,     // fetch_interval_ms
        32.45f,     // latitude
        34.91f,     // longitude
        10800,      // tz_offset
        settings_data1,
        settings_data2
    );

    SettingsData settings(settings_data1, settings_data2);
    uint8_t settings_crc = settings.CalculateCRC();

    std::cout << "  ✓ SettingsData created\n";
    std::cout << "    - Brightness: " << (int)settings.GetBrightness() << "%\n";
    std::cout << "    - Latitude: " << settings.GetLatitude() << "°\n";
    std::cout << "    - Longitude: " << settings.GetLongitude() << "°\n";
    std::cout << "    - TZ offset: " << settings.GetTzOffset() << "s\n";
    std::cout << "    - CRC: 0x" << std::hex << (int)settings_crc << std::dec << "\n\n";

    // Build 26-byte message
    std::cout << "Test 2: Building 26-byte message...\n";
    std::vector<uint8_t> message(26);

    // SurfData: bytes 0-7
    for (int i = 0; i < 8; i++) {
        message[i] = (surf_packed >> (56 - i*8)) & 0xFF;
    }
    message[8] = surf_crc;

    // SettingsData: bytes 9-16 and 17-24
    for (int i = 0; i < 8; i++) {
        message[9+i] = (settings_data1 >> (56 - i*8)) & 0xFF;
        message[17+i] = (settings_data2 >> (56 - i*8)) & 0xFF;
    }
    message[25] = settings_crc;

    std::cout << "  ✓ Message bytes: ";
    for (int i = 0; i < 26; i++) {
        std::cout << std::hex << (int)message[i] << " ";
    }
    std::cout << std::dec << "\n\n";

    // Test 3: Parse message
    std::cout << "Test 3: Parsing message...\n";
    auto msg = handler.parse(message);

    if (msg == nullptr) {
        std::cout << "  ✗ Parse failed!\n";
        return 1;
    }

    std::cout << "  ✓ Message parsed successfully\n";
    std::cout << "    - Reference count: " << msg.use_count() << "\n";

    // Test 4: Verify data
    std::cout << "\nTest 4: Verifying parsed data...\n";
    std::cout << "  Wave height: " << (int)msg->surf.GetWaveHeight() << " cm (expected 150)\n";
    std::cout << "  Wave period: " << (int)msg->surf.GetWavePeriod() << " s (expected 12)\n";
    std::cout << "  Wind speed: " << (int)msg->surf.GetWindSpeed() << " m/s (expected 25)\n";
    std::cout << "  Brightness: " << (int)msg->settings.GetBrightness() << "% (expected 80)\n";
    std::cout << "  Latitude: " << msg->settings.GetLatitude() << "° (expected 32.45)\n";
    std::cout << "  Longitude: " << msg->settings.GetLongitude() << "° (expected 34.91)\n";

    if (msg->surf.GetWaveHeight() == 150 &&
        msg->surf.GetWavePeriod() == 12 &&
        msg->surf.GetWindSpeed() == 25 &&
        msg->settings.GetBrightness() == 80) {
        std::cout << "  ✓ All values correct!\n";
    } else {
        std::cout << "  ✗ Some values incorrect!\n";
        return 1;
    }

    // Test 5: Shared ownership
    std::cout << "\nTest 5: Testing shared ownership...\n";
    auto msg2 = msg;   // Consumer 1
    auto msg3 = msg;   // Consumer 2
    auto msg4 = msg;   // Consumer 3

    std::cout << "  Reference count after copies: " << msg.use_count() << " (expected 4)\n";

    if (msg.get() == msg2.get() && msg.get() == msg3.get() && msg.get() == msg4.get()) {
        std::cout << "  ✓ All pointers point to same object!\n";
    } else {
        std::cout << "  ✗ Pointers don't match!\n";
        return 1;
    }

    msg2.reset();
    std::cout << "  After msg2.reset(): use_count = " << msg.use_count() << " (expected 3)\n";

    // Test 6: Statistics
    std::cout << "\nTest 6: Statistics...\n";
    std::cout << "  Total parsed: " << handler.getTotalParsed() << " (expected 1)\n";
    std::cout << "  Validation failures: " << handler.getValidationFailures() << " (expected 0)\n";

    if (handler.getTotalParsed() == 1 && handler.getValidationFailures() == 0) {
        std::cout << "  ✓ Statistics correct!\n";
    } else {
        std::cout << "  ✗ Statistics incorrect!\n";
        return 1;
    }

    // Test 7: Invalid CRC
    std::cout << "\nTest 7: Testing CRC validation...\n";
    message[8] ^= 0xFF;  // Corrupt surf CRC

    auto msg_bad = handler.parse(message);
    if (msg_bad == nullptr) {
        std::cout << "  ✓ Correctly rejected corrupted message\n";
    } else {
        std::cout << "  ✗ Should have rejected corrupted message!\n";
        return 1;
    }

    std::cout << "  Validation failures now: " << handler.getValidationFailures() << " (expected 1)\n";

    std::cout << "\n=======================\n";
    std::cout << "✓ All tests passed!\n";
    return 0;
}
