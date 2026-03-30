#ifndef MESSAGE_WRAPPER_H
#define MESSAGE_WRAPPER_H

#include <memory>
#include <vector>
#include <chrono>
#include <atomic>
#include "../../my_lib/esp_Server_encoding.hpp"


class ParsedMessage
{
public:
    ParsedMessage(const SurfData& surf, const SettingsData& settings);

    SurfData surf;
    SettingsData settings;
    std::chrono::system_clock::time_point received_at;
};

class MessageHandler 
{
public:
    MessageHandler();

    // Parse 26-byte message, return shared ownership
    // Returns nullptr on validation failure
    std::shared_ptr<ParsedMessage> parse(const std::vector<uint8_t>& raw_bytes);

    // Statistics
    uint64_t getTotalParsed() const;
    uint64_t getValidationFailures() const;

private:
    std::atomic<uint64_t> total_parsed_{0};
    std::atomic<uint64_t> validation_failures_{0};
};

#endif // MESSAGE_WRAPPER_H
