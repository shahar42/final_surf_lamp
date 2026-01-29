#include "esp_Server_encoding.hpp"
#include <iostream>
#include <iomanip>

int main() {
    // Test packing (simulating real surf data)
    uint8_t period = 12;              // 6 bits - wave period in seconds
    uint16_t height = 150;            // 10 bits - wave height in cm
    uint16_t wave_threshold = 100;    // 10 bits - threshold for wave alert
    uint16_t speed = 25;              // 10 bits - wind speed in m/s
    uint8_t wind_threshold = 22;      // 7 bits - threshold for wind alert
    uint16_t direction = 270;         // 10 bits - wind direction in degrees
    bool stale = false;
    bool available = true;
    bool quiet = false;
    bool off = false;

    uint64_t packed = SurfData::PackData(period, height, wave_threshold,
                                         speed, wind_threshold, direction,
                                         stale, available, quiet, off);

    std::cout << "Packed value: 0x" << std::hex << packed << std::dec << std::endl;
    std::cout << "Size: 8 bytes (vs ~450 bytes JSON)" << std::endl;

    // Test unpacking
    SurfData surf(packed);

    std::cout << "\n=== Current Readings ===" << std::endl;
    std::cout << "Wave Period: " << (int)surf.GetWavePeriod() << " seconds" << std::endl;
    std::cout << "Wave Height: " << surf.GetWaveHeight() << " cm" << std::endl;
    std::cout << "Wind Speed: " << surf.GetWindSpeed() << " m/s" << std::endl;
    std::cout << "Wind Direction: " << surf.GetWindDirection() << " degrees" << std::endl;

    std::cout << "\n=== Thresholds ===" << std::endl;
    std::cout << "Wave Threshold: " << surf.GetWaveThreshold() << " cm" << std::endl;
    std::cout << "Wind Threshold: " << (int)surf.GetWindThreshold() << " knots" << std::endl;

    std::cout << "\n=== Flags ===" << std::endl;
    std::cout << "Stale Data: " << (surf.GetStaleData() ? "Yes" : "No") << std::endl;
    std::cout << "Data Available: " << (surf.GetDataAvailable() ? "Yes" : "No") << std::endl;
    std::cout << "Quiet Hours: " << (surf.GetQuietHours() ? "Yes" : "No") << std::endl;
    std::cout << "Off Hours: " << (surf.GetOffHours() ? "Yes" : "No") << std::endl;

    // Verify round-trip
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

    std::cout << "\n=== Round-trip test: " << (success ? "PASSED ✓" : "FAILED ✗") << " ===" << std::endl;

    return success ? 0 : 1;
}
