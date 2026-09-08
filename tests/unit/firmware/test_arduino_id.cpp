// getArduinoId() from Config.h: MAC -> 24-bit device ID.
// getArduinoId caches in a static, so each MAC case runs as its own process:
//   test_arduino_id <mac_hex> <expected_id>
#include <cstdlib>

#include "check.h"
#include "Config.h"

WaveConfig waveConfig;
LEDMappingConfig ledMapping;

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s <mac_hex> <expected_id>\n", argv[0]);
        return 2;
    }
    uint64_t mac = std::strtoull(argv[1], nullptr, 16);
    uint32_t expected = static_cast<uint32_t>(std::strtoul(argv[2], nullptr, 10));

    ESP.efuseMac = mac;

    TEST(id_derived_from_low_three_nic_bytes) {
        uint32_t id = getArduinoId();
        CHECK_EQ(id, expected);
    }

    TEST(id_fits_24_bits_and_is_never_zero) {
        uint32_t id = getArduinoId();
        CHECK(id >= 1);
        CHECK(id <= 16777215u);
    }

    TEST(id_is_cached_after_first_call) {
        uint32_t first = getArduinoId();
        ESP.efuseMac = ~mac;                 // a different chip, hypothetically
        CHECK_EQ(getArduinoId(), first);     // still the value from boot
    }

    TEST(ARDUINO_ID_macro_matches_function) {
        CHECK_EQ((uint32_t)ARDUINO_ID, getArduinoId());
    }

    return check::summary("test_arduino_id");
}
