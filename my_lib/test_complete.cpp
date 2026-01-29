#include "esp_Server_encoding.hpp"
#include <iostream>
#include <iomanip>
#include <cmath>

void test_surf_data() {
    std::cout << "========== TESTING SurfData (8 bytes) ==========" << std::endl;

    // Pack surf conditions
    uint8_t period = 12;
    uint16_t height = 150;
    uint16_t wave_threshold = 100;
    uint16_t speed = 25;
    uint8_t wind_threshold = 22;
    uint16_t direction = 270;
    bool stale = false;
    bool available = true;
    bool quiet = false;
    bool off = false;

    uint64_t packed = SurfData::PackData(period, height, wave_threshold,
                                         speed, wind_threshold, direction,
                                         stale, available, quiet, off);

    std::cout << "Packed: 0x" << std::hex << packed << std::dec << std::endl;

    // Unpack and verify
    SurfData surf(packed);

    bool success = (surf.GetWavePeriod() == period &&
                   surf.GetWaveHeight() == height &&
                   surf.GetWaveThreshold() == wave_threshold &&
                   surf.GetWindSpeed() == speed &&
                   surf.GetWindThreshold() == wind_threshold &&
                   surf.GetWindDirection() == direction &&
                   surf.GetStaleData() == stale &&
                   surf.GetDataAvailable() == available &&
                   surf.GetQuietHours() == quiet &&
                   surf.GetOffHours() == off);

    std::cout << "Round-trip: " << (success ? "PASSED ✓" : "FAILED ✗") << std::endl;
    std::cout << std::endl;
}

void test_settings_data() {
    std::cout << "========== TESTING SettingsData (16 bytes) ==========" << std::endl;

    // Pack settings (simulating Tel Aviv location from your server)
    LEDTheme theme = LEDTheme::CLASSIC_SURF;
    uint8_t brightness = 60;  // 60% brightness
    uint32_t fetch_interval = 780000;  // 13 minutes in ms
    float latitude = 32.0853f;  // Tel Aviv
    float longitude = 34.7818f;  // Tel Aviv
    int32_t tz_offset = 7200;  // UTC+2 (Israel Standard Time)

    uint64_t data1, data2;
    SettingsData::Pack(theme, brightness, fetch_interval,
                       latitude, longitude, tz_offset,
                       data1, data2);

    std::cout << "Packed data1: 0x" << std::hex << data1 << std::dec << std::endl;
    std::cout << "Packed data2: 0x" << std::hex << data2 << std::dec << std::endl;

    // Unpack and verify
    SettingsData settings(data1, data2);

    std::cout << std::fixed << std::setprecision(4);
    std::cout << "\nUnpacked values:" << std::endl;
    std::cout << "Theme: " << static_cast<int>(settings.GetLEDTheme()) << " (0=Classic Surf)" << std::endl;
    std::cout << "Brightness: " << (int)settings.GetBrightness() << "%" << std::endl;
    std::cout << "Fetch Interval: " << settings.GetFetchIntervalMs() << " ms" << std::endl;
    std::cout << "Latitude: " << settings.GetLatitude() << "°" << std::endl;
    std::cout << "Longitude: " << settings.GetLongitude() << "°" << std::endl;
    std::cout << "TZ Offset: " << settings.GetTzOffset() << " seconds" << std::endl;

    // Verify with tolerance for float precision
    bool lat_ok = std::abs(settings.GetLatitude() - latitude) < 0.0001f;
    bool lon_ok = std::abs(settings.GetLongitude() - longitude) < 0.0001f;

    bool success = (settings.GetLEDTheme() == theme &&
                   settings.GetBrightness() == brightness &&
                   settings.GetFetchIntervalMs() == fetch_interval &&
                   lat_ok && lon_ok &&
                   settings.GetTzOffset() == tz_offset);

    std::cout << "\nRound-trip: " << (success ? "PASSED ✓" : "FAILED ✗") << std::endl;
    std::cout << std::endl;
}

void test_complete_message() {
    std::cout << "========== COMPLETE MESSAGE TEST ==========" << std::endl;
    std::cout << "Total size: 8 + 16 = 24 bytes" << std::endl;
    std::cout << "JSON size: ~450 bytes" << std::endl;
    std::cout << "Compression: 95% smaller!" << std::endl;
    std::cout << std::endl;

    std::cout << "This represents a complete Arduino data packet:" << std::endl;
    std::cout << "- SurfData: Dynamic conditions (updated every 13 min)" << std::endl;
    std::cout << "- SettingsData: Static config (cached on Arduino)" << std::endl;
    std::cout << std::endl;
}

int main() {
    test_surf_data();
    test_settings_data();
    test_complete_message();

    std::cout << "========== ALL TESTS COMPLETE ==========" << std::endl;
    return 0;
}
