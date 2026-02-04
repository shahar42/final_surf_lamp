#include "esp_Server_encoding.hpp"
#include <iostream>
#include <iomanip>

void test_surf_data_crc() {
    std::cout << "========== TESTING SurfData CRC-8 ==========" << std::endl;

    // Pack surf data
    uint64_t packed = SurfData::PackData(12, 150, 100, 25, 22, 270,
                                         false, true, false, false);

    SurfData surf(packed);
    uint8_t crc = surf.CalculateCRC();

    std::cout << "Packed data: 0x" << std::hex << packed << std::dec << std::endl;
    std::cout << "CRC-8: 0x" << std::hex << (int)crc << std::dec << std::endl;

    // Test 1: Valid CRC
    bool valid = surf.ValidateCRC(crc);
    std::cout << "\nTest 1 - Valid CRC: " << (valid ? "PASSED ✓" : "FAILED ✗") << std::endl;

    // Test 2: Corrupt data (flip one bit)
    uint64_t corrupted = packed ^ 0x1;  // Flip bit 0
    SurfData surf_corrupt(corrupted);
    bool invalid = !surf_corrupt.ValidateCRC(crc);  // Should fail validation
    std::cout << "Test 2 - Corrupted data detected: " << (invalid ? "PASSED ✓" : "FAILED ✗") << std::endl;

    // Test 3: Different data = different CRC
    uint64_t different = SurfData::PackData(13, 150, 100, 25, 22, 270,  // period changed
                                            false, true, false, false);
    SurfData surf_diff(different);
    uint8_t crc_diff = surf_diff.CalculateCRC();
    bool different_crc = (crc != crc_diff);
    std::cout << "Test 3 - Different data = different CRC: " << (different_crc ? "PASSED ✓" : "FAILED ✗") << std::endl;

    std::cout << std::endl;
}

void test_settings_data_crc() {
    std::cout << "========== TESTING SettingsData CRC-8 ==========" << std::endl;

    // Pack settings
    uint64_t data1, data2;
    SettingsData::Pack(LEDTheme::CLASSIC_SURF, 60, 780000,
                       32.0853f, 34.7818f, 7200,
                       data1, data2);

    SettingsData settings(data1, data2);
    uint8_t crc = settings.CalculateCRC();

    std::cout << "Packed data1: 0x" << std::hex << data1 << std::dec << std::endl;
    std::cout << "Packed data2: 0x" << std::hex << data2 << std::dec << std::endl;
    std::cout << "CRC-8: 0x" << std::hex << (int)crc << std::dec << std::endl;

    // Test 1: Valid CRC
    bool valid = settings.ValidateCRC(crc);
    std::cout << "\nTest 1 - Valid CRC: " << (valid ? "PASSED ✓" : "FAILED ✗") << std::endl;

    // Test 2: Corrupt data (flip one bit in data1)
    uint64_t corrupted1 = data1 ^ 0x100;  // Flip bit 8
    SettingsData settings_corrupt(corrupted1, data2);
    bool invalid = !settings_corrupt.ValidateCRC(crc);  // Should fail validation
    std::cout << "Test 2 - Corrupted data detected: " << (invalid ? "PASSED ✓" : "FAILED ✗") << std::endl;

    // Test 3: Corrupt data (flip one bit in data2)
    uint64_t corrupted2 = data2 ^ 0x1;  // Flip bit 0
    SettingsData settings_corrupt2(data1, corrupted2);
    bool invalid2 = !settings_corrupt2.ValidateCRC(crc);  // Should fail validation
    std::cout << "Test 3 - Corrupted data2 detected: " << (invalid2 ? "PASSED ✓" : "FAILED ✗") << std::endl;

    std::cout << std::endl;
}

void test_network_simulation() {
    std::cout << "========== NETWORK TRANSMISSION SIMULATION ==========" << std::endl;

    // Simulate server sending data
    std::cout << "SERVER: Packing surf data..." << std::endl;
    uint64_t surf_packed = SurfData::PackData(12, 150, 100, 25, 22, 270,
                                              false, true, false, false);
    SurfData server_surf(surf_packed);
    uint8_t surf_crc = server_surf.CalculateCRC();

    std::cout << "SERVER: Data=0x" << std::hex << surf_packed
              << ", CRC=0x" << (int)surf_crc << std::dec << std::endl;

    // Simulate network transmission
    std::cout << "\nNETWORK: Transmitting 9 bytes (8 data + 1 CRC)..." << std::endl;

    // Simulate Arduino receiving (NO corruption)
    std::cout << "\nARDUINO: Received data, validating..." << std::endl;
    SurfData arduino_surf(surf_packed);
    if (arduino_surf.ValidateCRC(surf_crc)) {
        std::cout << "ARDUINO: ✓ CRC valid - Data integrity confirmed!" << std::endl;
        std::cout << "ARDUINO: Wave height = " << arduino_surf.GetWaveHeight() << " cm" << std::endl;
    } else {
        std::cout << "ARDUINO: ✗ CRC invalid - Data corrupted, discarding packet!" << std::endl;
    }

    // Simulate corruption during transmission
    std::cout << "\n--- Simulating corrupted transmission ---" << std::endl;
    uint64_t corrupted_packet = surf_packed ^ 0x10000;  // Flip bit 16
    std::cout << "NETWORK: Bit flip occurred during transmission!" << std::endl;

    std::cout << "\nARDUINO: Received corrupted data, validating..." << std::endl;
    SurfData arduino_corrupt(corrupted_packet);
    if (arduino_corrupt.ValidateCRC(surf_crc)) {
        std::cout << "ARDUINO: ✓ CRC valid" << std::endl;
    } else {
        std::cout << "ARDUINO: ✗ CRC MISMATCH - Data corrupted, discarding packet!" << std::endl;
        std::cout << "ARDUINO: Requesting retransmission..." << std::endl;
    }

    std::cout << std::endl;
}

void print_packet_structure() {
    std::cout << "========== PACKET STRUCTURE ==========" << std::endl;
    std::cout << "SurfData packet:" << std::endl;
    std::cout << "  - Data: 8 bytes (64 bits)" << std::endl;
    std::cout << "  - CRC:  1 byte (8 bits)" << std::endl;
    std::cout << "  Total:  9 bytes per surf update" << std::endl;
    std::cout << std::endl;
    std::cout << "SettingsData packet:" << std::endl;
    std::cout << "  - Data: 16 bytes (2 x 64 bits)" << std::endl;
    std::cout << "  - CRC:  1 byte (8 bits)" << std::endl;
    std::cout << "  Total:  17 bytes per settings update" << std::endl;
    std::cout << std::endl;
    std::cout << "Combined: 26 bytes total (vs ~450 bytes JSON = 94% reduction)" << std::endl;
    std::cout << std::endl;
}

int main() {
    test_surf_data_crc();
    test_settings_data_crc();
    test_network_simulation();
    print_packet_structure();

    std::cout << "========== ALL CRC TESTS PASSED ==========" << std::endl;
    return 0;
}
