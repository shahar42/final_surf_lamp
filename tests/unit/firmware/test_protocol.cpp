// Firmware side of the V3 protocol: pack/unpack round-trips, CRC vectors,
// corruption detection, and PARITY with the server encoder via a fixture
// produced by cpp_message_wrapper/cpp_encoder.py (see gen_v3_fixture.py).
//
// Usage: test_protocol <fixture.bin> <fixture.txt>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "check.h"
#include "esp_Server_encoding.hpp"   // the FIRMWARE copy, via -I

static std::vector<uint8_t> read_bin(const char* path) {
    std::ifstream f(path, std::ios::binary);
    return std::vector<uint8_t>((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

static std::map<std::string, double> read_kv(const char* path) {
    std::map<std::string, double> kv;
    std::ifstream f(path);
    std::string line;
    while (std::getline(f, line)) {
        auto eq = line.find('=');
        if (eq == std::string::npos || line.empty() || line[0] == '#') continue;
        kv[line.substr(0, eq)] = std::stod(line.substr(eq + 1));
    }
    return kv;
}

static uint64_t be64(const std::vector<uint8_t>& b, size_t off) {
    uint64_t v = 0;
    for (size_t i = 0; i < 8; ++i) v = (v << 8) | b[off + i];
    return v;
}

int main(int argc, char** argv) {
    TEST(pack_unpack_surf_roundtrip) {
        uint64_t raw = SurfDataPacket::PackData(8, 120, 100, 5, 15, 270, false, true, false, true);
        SurfDataPacket p(raw);
        CHECK_EQ(p.GetWavePeriod(), 8);
        CHECK_EQ(p.GetWaveHeight(), 120);
        CHECK_EQ(p.GetWaveThreshold(), 100);
        CHECK_EQ(p.GetWindSpeed(), 5);
        CHECK_EQ(p.GetWindThreshold(), 15);
        CHECK_EQ(p.GetWindDirection(), 270);
        CHECK(p.GetStaleData() == false);
        CHECK(p.GetDataAvailable() == true);
        CHECK(p.GetQuietHours() == false);
        CHECK(p.GetOffHours() == true);
    }

    TEST(field_maxima_fit) {
        uint64_t raw = SurfDataPacket::PackData(63, 1023, 1023, 1023, 127, 1023, true, true, true, true);
        SurfDataPacket p(raw);
        CHECK_EQ(p.GetWavePeriod(), 63);
        CHECK_EQ(p.GetWaveHeight(), 1023);
        CHECK_EQ(p.GetWaveThreshold(), 1023);
        CHECK_EQ(p.GetWindSpeed(), 1023);
        CHECK_EQ(p.GetWindThreshold(), 127);
        CHECK_EQ(p.GetWindDirection(), 1023);
    }

    TEST(flags_are_independent_bits) {
        uint64_t only_off = SurfDataPacket::PackData(0, 0, 0, 0, 0, 0, false, false, false, true);
        SurfDataPacket p(only_off);
        CHECK(!p.GetStaleData() && !p.GetDataAvailable() && !p.GetQuietHours() && p.GetOffHours());
        CHECK_EQ(only_off, (uint64_t)1 << 56);
    }

    TEST(pack_unpack_settings_roundtrip) {
        uint64_t d1, d2;
        SettingsData::Pack(LEDTheme::OCEAN_SUNSET, 30, 780000, 32.4425f, 34.8683f, 7200, d1, d2);
        SettingsData s(d1, d2);
        CHECK(s.GetLEDTheme() == LEDTheme::OCEAN_SUNSET);
        CHECK_EQ(s.GetBrightness(), 30);
        CHECK_EQ(s.GetFetchIntervalMs(), 780000u);
        CHECK_NEAR(s.GetLatitude(), 32.4425, 2e-4);
        CHECK_NEAR(s.GetLongitude(), 34.8683, 2e-4);
        CHECK_EQ(s.GetTzOffset(), 7200);
    }

    TEST(negative_coordinates_and_tz_roundtrip) {
        uint64_t d1, d2;
        SettingsData::Pack(LEDTheme::CLASSIC_SURF, 100, 60000, -33.8688f, -70.6693f, -18000, d1, d2);
        SettingsData s(d1, d2);
        CHECK_NEAR(s.GetLatitude(), -33.8688, 2e-4);
        CHECK_NEAR(s.GetLongitude(), -70.6693, 2e-4);
        CHECK_EQ(s.GetTzOffset(), -18000);
    }

    TEST(crc8_known_vectors) {
        const uint8_t check_str[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
        CHECK_EQ((int)CRC8::Calculate(check_str, 9), 0xF4);   // standard CRC-8 check value
        const uint8_t zero = 0x00, one = 0x01;
        CHECK_EQ((int)CRC8::Calculate(&zero, 1), 0x00);
        CHECK_EQ((int)CRC8::Calculate(&one, 1), 0x07);
        CHECK_EQ((int)CRC8::Calculate((uint64_t)0), 0x00);
    }

    TEST(crc_validate_agrees_with_calculate) {
        SurfDataPacket p(0xDEADBEEFCAFEBABEULL);
        CHECK(p.ValidateCRC(p.CalculateCRC()));
        CHECK(!p.ValidateCRC(p.CalculateCRC() ^ 0x01));
    }

    TEST(corrupted_bit_fails_validate) {
        uint64_t raw = SurfDataPacket::PackData(8, 120, 100, 5, 15, 270, false, true, false, false);
        uint8_t crc = SurfDataPacket(raw).CalculateCRC();
        for (int bit = 0; bit < 57; bit += 7) {
            SurfDataPacket corrupt(raw ^ ((uint64_t)1 << bit));
            CHECK(!corrupt.ValidateCRC(crc));
        }
    }

    if (argc >= 3) {
        TEST(parity_with_python_encoder) {
            auto bytes = read_bin(argv[1]);
            auto want = read_kv(argv[2]);
            CHECK_EQ(bytes.size(), (size_t)26);
            if (bytes.size() == 26) {
                SurfDataPacket surf(be64(bytes, 0));
                CHECK(surf.ValidateCRC(bytes[8]));
                CHECK_EQ(surf.GetWavePeriod(), (int)want["wave_period_s"]);
                CHECK_EQ(surf.GetWaveHeight(), (int)want["wave_height_cm"]);
                CHECK_EQ(surf.GetWaveThreshold(), (int)want["wave_threshold_cm"]);
                CHECK_EQ(surf.GetWindSpeed(), (int)want["wind_speed_mps"]);
                CHECK_EQ(surf.GetWindThreshold(), (int)want["wind_speed_threshold_knots"]);
                CHECK_EQ(surf.GetWindDirection(), (int)want["wind_direction_deg"]);
                CHECK_EQ((int)surf.GetStaleData(), (int)want["stale_data_warning"]);
                CHECK_EQ((int)surf.GetDataAvailable(), (int)want["data_available"]);
                CHECK_EQ((int)surf.GetQuietHours(), (int)want["quiet_hours_active"]);
                CHECK_EQ((int)surf.GetOffHours(), (int)want["off_hours_active"]);

                SettingsData st(be64(bytes, 9), be64(bytes, 17));
                CHECK(st.ValidateCRC(bytes[25]));
                CHECK_EQ((int)st.GetLEDTheme(), (int)want["led_theme_index"]);
                CHECK_EQ((int)st.GetBrightness(), (int)want["brightness_pct"]);
                CHECK_EQ(st.GetFetchIntervalMs(), (uint32_t)want["fetch_interval_ms"]);
                CHECK_NEAR(st.GetLatitude(), want["latitude"], 2e-4);
                CHECK_NEAR(st.GetLongitude(), want["longitude"], 2e-4);
                CHECK_EQ(st.GetTzOffset(), (int32_t)want["tz_offset"]);
            }
        }
    } else {
        std::printf("- parity_with_python_encoder SKIPPED (no fixture args)\n");
    }

    return check::summary("test_protocol");
}
