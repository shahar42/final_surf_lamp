// JitterManager: thundering-herd spread derived from ARDUINO_ID.
#include "check.h"
#include "Config.h"
#include "JitterManager.h"

WaveConfig waveConfig;
LEDMappingConfig ledMapping;

int main() {
    ESP.efuseMac = 0x00112233445566ULL;   // id = 0x112233 = 1122867

    TEST(seed_is_the_arduino_id) {
        CHECK_EQ(JitterManager::getJitterSeed(), (unsigned long)getArduinoId());
    }

    TEST(startup_jitter_within_120s) {
        CHECK(JitterManager::getStartupJitterMs() < JitterManager::STARTUP_WINDOW_SEC * 1000);
        CHECK_EQ(JitterManager::getStartupJitterMs() % 1000, 0ul);
    }

    TEST(reconnect_jitter_within_60s) {
        CHECK(JitterManager::getReconnectJitterMs() < JitterManager::RECONNECT_WINDOW_SEC * 1000);
    }

    TEST(interval_shift_within_120s) {
        CHECK(JitterManager::getIntervalPhaseShiftMs() < JitterManager::INTERVAL_WINDOW_SEC * 1000);
    }

    TEST(jitter_deterministic_per_id) {
        CHECK_EQ(JitterManager::getStartupJitterMs(), JitterManager::getStartupJitterMs());
        CHECK_EQ(JitterManager::getStartupJitterMs(), (1122867ul % 120) * 1000);
        CHECK_EQ(JitterManager::getReconnectJitterMs(), (1122867ul % 60) * 1000);
    }

    TEST(mac_derived_ids_spread_evenly_over_startup_window) {
        // Same formula the manager uses, over 1200 consecutive NIC values.
        int buckets[120] = {0};
        for (unsigned long id = 0x100000; id < 0x100000 + 1200; ++id) buckets[id % 120]++;
        int lo = 1 << 30, hi = 0;
        for (int b : buckets) { if (b < lo) lo = b; if (b > hi) hi = b; }
        CHECK_EQ(lo, 10);
        CHECK_EQ(hi, 10);
    }

    return check::summary("test_jitter");
}
