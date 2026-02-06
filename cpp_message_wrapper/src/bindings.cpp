#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/chrono.h>
#include "message_wrapper.h"

namespace py = pybind11;

PYBIND11_MODULE(message_wrapper, m)
{
    m.doc() = "C++ message parser with shared_ptr for Surf Lamp";

    // Expose LEDTheme enum
    py::enum_<LEDTheme>(m, "LEDTheme")
        .value("CLASSIC_SURF", LEDTheme::CLASSIC_SURF)
        .value("VIBRANT_MIX", LEDTheme::VIBRANT_MIX)
        .value("TROPICAL_PARADISE", LEDTheme::TROPICAL_PARADISE)
        .value("OCEAN_SUNSET", LEDTheme::OCEAN_SUNSET)
        .value("ELECTRIC_VIBES", LEDTheme::ELECTRIC_VIBES);

    // Expose SurfData class
    py::class_<SurfData>(m, "SurfData")
        .def(py::init<uint64_t>())
        .def("get_wave_period", &SurfData::GetWavePeriod)
        .def("get_wave_height", &SurfData::GetWaveHeight)
        .def("get_wave_threshold", &SurfData::GetWaveThreshold)
        .def("get_wind_speed", &SurfData::GetWindSpeed)
        .def("get_wind_threshold", &SurfData::GetWindThreshold)
        .def("get_wind_direction", &SurfData::GetWindDirection)
        .def("get_stale_data", &SurfData::GetStaleData)
        .def("get_data_available", &SurfData::GetDataAvailable)
        .def("get_quiet_hours", &SurfData::GetQuietHours)
        .def("get_off_hours", &SurfData::GetOffHours)
        .def("calculate_crc", &SurfData::CalculateCRC)
        .def("validate_crc", &SurfData::ValidateCRC)
        .def_static("pack_data", &SurfData::PackData);

    // Expose SettingsData class
    py::class_<SettingsData>(m, "SettingsData")
        .def(py::init<uint64_t, uint64_t>())
        .def("get_led_theme", &SettingsData::GetLEDTheme)
        .def("get_brightness", &SettingsData::GetBrightness)
        .def("get_fetch_interval_ms", &SettingsData::GetFetchIntervalMs)
        .def("get_latitude", &SettingsData::GetLatitude)
        .def("get_longitude", &SettingsData::GetLongitude)
        .def("get_tz_offset", &SettingsData::GetTzOffset)
        .def("calculate_crc", &SettingsData::CalculateCRC)
        .def("validate_crc", &SettingsData::ValidateCRC)
        .def_static("pack", [](
            LEDTheme theme, uint8_t brightness, uint32_t fetch_interval_ms,
            float latitude, float longitude, int32_t tz_offset
        ) {
            uint64_t data1 = 0, data2 = 0;
            SettingsData::Pack(theme, brightness, fetch_interval_ms, latitude, longitude, tz_offset, data1, data2);
            return py::make_tuple(data1, data2);
        });

    // Expose ParsedMessage class with shared_ptr holder
    py::class_<ParsedMessage, std::shared_ptr<ParsedMessage>>(m, "ParsedMessage")
        .def_readonly("surf", &ParsedMessage::surf)
        .def_readonly("settings", &ParsedMessage::settings)
        .def_readonly("received_at", &ParsedMessage::received_at);

    // Expose MessageHandler class
    py::class_<MessageHandler>(m, "MessageHandler")
        .def(py::init<>())
        .def("parse", &MessageHandler::parse, "Parse 26-byte binary message")
        .def("get_total_parsed", &MessageHandler::getTotalParsed)
        .def("get_validation_failures", &MessageHandler::getValidationFailures);
}
