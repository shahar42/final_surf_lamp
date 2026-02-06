#include "message_wrapper.h"

MessageHandler::MessageHandler() {}

ParsedMessage::ParsedMessage(const SurfData& surf, const SettingsData& settings)
    : surf(surf), settings(settings), received_at(std::chrono::system_clock::now())
{
}

uint64_t MessageHandler::getTotalParsed() const
{
    return total_parsed_;
}

uint64_t MessageHandler::getValidationFailures() const
{
    return validation_failures_;
}

std::shared_ptr<ParsedMessage> MessageHandler::parse(const std::vector<uint8_t>& raw_bytes)
{
    if(raw_bytes.size() != 26)
    {
        validation_failures_++;
        return nullptr;
    }

    // Extract SurfData (bytes 0-7)
    uint64_t surf_data = 0;
    for(int i = 0; i < 8; ++i)
    {
        surf_data |= ((uint64_t)raw_bytes[i]) << (56 - i*8);
    }

    SurfData surf(surf_data);
    if(!surf.ValidateCRC(raw_bytes[8]))
    {
        validation_failures_++;
        return nullptr;
    }

    // Extract SettingsData (bytes 9-16 and 17-24)
    uint64_t setting_data1 = 0;
    uint64_t setting_data2 = 0;
    for(int i = 0; i < 8; ++i)
    {
        setting_data1 |= ((uint64_t)raw_bytes[i+9]) << (56 - i*8);
        setting_data2 |= ((uint64_t)raw_bytes[i+17]) << (56 - i*8);
    }

    SettingsData settings(setting_data1, setting_data2);
    if(!settings.ValidateCRC(raw_bytes[25]))
    {
        validation_failures_++;
        return nullptr;
    }

    total_parsed_++;
    return std::make_shared<ParsedMessage>(surf, settings);
}








