#include <gtest/gtest.h>
#include "../include/message_wrapper.h"
#include "../../web_and_database/binary_protocol.py"
#include <memory>

// Helper: Generate a valid 26-byte test message
std::vector<uint8_t> getValidTestMessage()
{
    // Test message with known good values
    // Using SurfData::PackData to create valid packed data
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

    // Settings data
    uint64_t settings_data1, settings_data2;
    SettingsData::Pack(
        LEDTheme::CLASSIC_SURF,  // theme
        80,                       // brightness
        300000,                   // fetch_interval_ms
        32.45f,                   // latitude
        34.91f,                   // longitude
        10800,                    // tz_offset
        settings_data1,
        settings_data2
    );

    SettingsData settings(settings_data1, settings_data2);
    uint8_t settings_crc = settings.CalculateCRC();

    // Build 26-byte message
    std::vector<uint8_t> message(26);

    // SurfData: bytes 0-7 (big-endian uint64_t)
    for (int i = 0; i < 8; i++) {
        message[i] = (surf_packed >> (56 - i*8)) & 0xFF;
    }
    message[8] = surf_crc;

    // SettingsData: bytes 9-16 and 17-24 (two big-endian uint64_t)
    for (int i = 0; i < 8; i++) {
        message[9+i] = (settings_data1 >> (56 - i*8)) & 0xFF;
        message[17+i] = (settings_data2 >> (56 - i*8)) & 0xFF;
    }
    message[25] = settings_crc;

    return message;
}

// ============================================================================
// TESTS FOR SHARED_PTR SEMANTICS
// ============================================================================

TEST(MessageWrapperTest, SharedOwnership)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    auto msg1 = handler.parse(raw);
    ASSERT_NE(msg1, nullptr);
    EXPECT_EQ(msg1.use_count(), 1);

    // Multiple consumers share ownership
    auto msg2 = msg1;  // Logger holds reference
    auto msg3 = msg1;  // Database holds reference
    auto msg4 = msg1;  // Broadcaster holds reference

    // All point to SAME object (pointer equality)
    EXPECT_EQ(msg1.get(), msg2.get());
    EXPECT_EQ(msg1.get(), msg3.get());
    EXPECT_EQ(msg1.get(), msg4.get());

    // Reference count = 4
    EXPECT_EQ(msg1.use_count(), 4);
}

TEST(MessageWrapperTest, ReferenceCountDecrement)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    auto msg1 = handler.parse(raw);
    ASSERT_NE(msg1, nullptr);

    auto msg2 = msg1;
    auto msg3 = msg1;
    auto msg4 = msg1;
    EXPECT_EQ(msg1.use_count(), 4);

    // Drop references one by one
    msg2.reset();
    EXPECT_EQ(msg1.use_count(), 3);

    msg3.reset();
    EXPECT_EQ(msg1.use_count(), 2);

    msg4.reset();
    EXPECT_EQ(msg1.use_count(), 1);

    // Still valid
    EXPECT_NE(msg1, nullptr);
}

TEST(MessageWrapperTest, HandlerDestroyedMessageSurvives)
{
    std::shared_ptr<ParsedMessage> msg;

    {
        MessageHandler handler;
        std::vector<uint8_t> raw = getValidTestMessage();
        msg = handler.parse(raw);
        ASSERT_NE(msg, nullptr);
    }  // handler destroyed

    // Message still valid! Shared ownership kept it alive
    EXPECT_EQ(msg.use_count(), 1);
    EXPECT_EQ(msg->surf.GetWavePeriod(), 12);
    EXPECT_EQ(msg->surf.GetWaveHeight(), 150);
}

// ============================================================================
// TESTS FOR PARSING AND VALIDATION
// ============================================================================

TEST(MessageWrapperTest, ValidMessage)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    auto msg = handler.parse(raw);
    ASSERT_NE(msg, nullptr);

    // Verify surf fields
    EXPECT_EQ(msg->surf.GetWavePeriod(), 12);
    EXPECT_EQ(msg->surf.GetWaveHeight(), 150);
    EXPECT_EQ(msg->surf.GetWaveThreshold(), 100);
    EXPECT_EQ(msg->surf.GetWindSpeed(), 25);
    EXPECT_EQ(msg->surf.GetWindThreshold(), 20);
    EXPECT_EQ(msg->surf.GetWindDirection(), 180);
    EXPECT_FALSE(msg->surf.GetStaleData());
    EXPECT_TRUE(msg->surf.GetDataAvailable());

    // Verify settings fields
    EXPECT_EQ(msg->settings.GetBrightness(), 80);
    EXPECT_EQ(msg->settings.GetFetchIntervalMs(), 300000);
    EXPECT_NEAR(msg->settings.GetLatitude(), 32.45f, 0.01f);
    EXPECT_NEAR(msg->settings.GetLongitude(), 34.91f, 0.01f);
    EXPECT_EQ(msg->settings.GetTzOffset(), 10800);
}

TEST(MessageWrapperTest, InvalidSurfCRC)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    // Corrupt surf CRC
    raw[8] ^= 0xFF;

    auto msg = handler.parse(raw);
    EXPECT_EQ(msg, nullptr);
    EXPECT_EQ(handler.getValidationFailures(), 1);
}

TEST(MessageWrapperTest, InvalidSettingsCRC)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    // Corrupt settings CRC
    raw[25] ^= 0xFF;

    auto msg = handler.parse(raw);
    EXPECT_EQ(msg, nullptr);
    EXPECT_EQ(handler.getValidationFailures(), 1);
}

TEST(MessageWrapperTest, TooShortMessage)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    // Remove 1 byte
    raw.pop_back();
    EXPECT_EQ(raw.size(), 25);

    auto msg = handler.parse(raw);
    EXPECT_EQ(msg, nullptr);
    EXPECT_EQ(handler.getValidationFailures(), 1);
}

TEST(MessageWrapperTest, TooLongMessage)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    // Add extra byte
    raw.push_back(0xFF);
    EXPECT_EQ(raw.size(), 27);

    auto msg = handler.parse(raw);
    EXPECT_EQ(msg, nullptr);
    EXPECT_EQ(handler.getValidationFailures(), 1);
}

// ============================================================================
// TESTS FOR STATISTICS
// ============================================================================

TEST(MessageWrapperTest, Statistics)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    EXPECT_EQ(handler.getTotalParsed(), 0);
    EXPECT_EQ(handler.getValidationFailures(), 0);

    // Parse 3 valid messages
    for (int i = 0; i < 3; i++) {
        auto msg = handler.parse(raw);
        EXPECT_NE(msg, nullptr);
    }
    EXPECT_EQ(handler.getTotalParsed(), 3);
    EXPECT_EQ(handler.getValidationFailures(), 0);

    // Parse 2 invalid messages
    std::vector<uint8_t> bad = raw;
    bad[8] ^= 0xFF;
    for (int i = 0; i < 2; i++) {
        auto msg = handler.parse(bad);
        EXPECT_EQ(msg, nullptr);
    }
    EXPECT_EQ(handler.getTotalParsed(), 3);
    EXPECT_EQ(handler.getValidationFailures(), 2);
}

// ============================================================================
// TESTS FOR TIMESTAMP
// ============================================================================

TEST(MessageWrapperTest, TimestampRecorded)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    auto before = std::chrono::system_clock::now();
    auto msg = handler.parse(raw);
    auto after = std::chrono::system_clock::now();

    ASSERT_NE(msg, nullptr);
    EXPECT_GE(msg->received_at, before);
    EXPECT_LE(msg->received_at, after);
}

// ============================================================================
// TESTS FOR MULTIPLE PARSES
// ============================================================================

TEST(MessageWrapperTest, MultipleParses)
{
    MessageHandler handler;
    std::vector<uint8_t> raw = getValidTestMessage();

    auto msg1 = handler.parse(raw);
    auto msg2 = handler.parse(raw);
    auto msg3 = handler.parse(raw);

    // Each parse creates a new object (different pointers)
    EXPECT_NE(msg1.get(), msg2.get());
    EXPECT_NE(msg2.get(), msg3.get());
    EXPECT_NE(msg1.get(), msg3.get());

    // But all have same data
    EXPECT_EQ(msg1->surf.GetWaveHeight(), msg2->surf.GetWaveHeight());
    EXPECT_EQ(msg2->surf.GetWaveHeight(), msg3->surf.GetWaveHeight());

    // Statistics should show 3 parses
    EXPECT_EQ(handler.getTotalParsed(), 3);
}

int main(int argc, char** argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
