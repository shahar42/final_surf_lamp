"""
Unit tests for cpp_message_wrapper/cpp_encoder.py (server side of the V3 protocol).

Every byte the lamp receives comes out of encode_v3_response_cpp. The tests
encode with the production encoder and decode with the C++ MessageHandler,
which shares esp_Server_encoding.hpp with the firmware, so a passing
round-trip here is the closest thing to "the lamp will read it correctly"
short of flashing hardware.
"""

import pytest

import message_wrapper
from cpp_encoder import encode_v3_response_cpp, theme_to_enum
from config import BRIGHTNESS_LEVELS

# Field widths from esp_Server_encoding.hpp (SurfDataBitsOffset / SettingsDataBitsOffset)
MAX_PERIOD = 0x3F          # 6 bits
MAX_HEIGHT_CM = 0x3FF      # 10 bits
MAX_WAVE_THRESH_CM = 0x3FF
MAX_WIND_MPS = 0x3FF
MAX_WIND_THRESH_KN = 0x7F  # 7 bits
MAX_DIRECTION = 0x3FF
MAX_INTERVAL_MS = 0xFFFFF  # 20 bits


def surf(**overrides):
    d = dict(
        wave_period_s=8, wave_height_cm=120, wave_threshold_cm=100,
        wind_speed_mps=5, wind_speed_threshold_knots=15, wind_direction_deg=270,
        stale_data_warning=False, data_available=True,
        quiet_hours_active=False, off_hours_active=False,
    )
    d.update(overrides)
    return d


def settings(**overrides):
    d = dict(
        led_theme="classic_surf", brightness_multiplier=0.3, fetch_interval_ms=13 * 60 * 1000,
        latitude=32.4425, longitude=34.8683, tz_offset=7200,
    )
    d.update(overrides)
    return d


def decode(packet: bytes):
    handler = message_wrapper.MessageHandler()
    parsed = handler.parse(list(packet))
    return parsed, handler


@pytest.mark.unit
class TestPacketShape:
    def test_output_is_exactly_26_bytes(self):
        packet = encode_v3_response_cpp(surf(), settings())
        assert isinstance(packet, bytes)
        assert len(packet) == 26

    def test_surf_crc_is_byte_8(self):
        packet = encode_v3_response_cpp(surf(), settings())
        raw = int.from_bytes(packet[0:8], "big")
        assert message_wrapper.SurfData(raw).calculate_crc() == packet[8]

    def test_settings_crc_is_byte_25(self):
        packet = encode_v3_response_cpp(surf(), settings())
        d1 = int.from_bytes(packet[9:17], "big")
        d2 = int.from_bytes(packet[17:25], "big")
        assert message_wrapper.SettingsData(d1, d2).calculate_crc() == packet[25]

    def test_parser_accepts_encoder_output(self):
        parsed, handler = decode(encode_v3_response_cpp(surf(), settings()))
        assert parsed is not None
        assert handler.get_total_parsed() == 1
        assert handler.get_validation_failures() == 0


@pytest.mark.unit
class TestSurfRoundTrip:
    def test_roundtrip_surf_fields(self):
        parsed, _ = decode(encode_v3_response_cpp(surf(), settings()))
        s = parsed.surf
        assert s.get_wave_period() == 8
        assert s.get_wave_height() == 120
        assert s.get_wave_threshold() == 100
        assert s.get_wind_speed() == 5
        assert s.get_wind_threshold() == 15
        assert s.get_wind_direction() == 270

    @pytest.mark.parametrize("flag,getter", [
        ("stale_data_warning", "get_stale_data"),
        ("data_available", "get_data_available"),
        ("quiet_hours_active", "get_quiet_hours"),
        ("off_hours_active", "get_off_hours"),
    ])
    def test_flags_independent(self, flag, getter):
        """Each flag toggled alone must move only its own bit."""
        base = surf(stale_data_warning=False, data_available=False, quiet_hours_active=False, off_hours_active=False)
        off, _ = decode(encode_v3_response_cpp(base, settings()))
        on, _ = decode(encode_v3_response_cpp({**base, flag: True}, settings()))
        for g in ("get_stale_data", "get_data_available", "get_quiet_hours", "get_off_hours"):
            assert getattr(off.surf, g)() is False
            assert getattr(on.surf, g)() is (g == getter)

    def test_max_in_range_values_survive(self):
        parsed, _ = decode(encode_v3_response_cpp(surf(
            wave_period_s=MAX_PERIOD, wave_height_cm=MAX_HEIGHT_CM, wave_threshold_cm=MAX_WAVE_THRESH_CM,
            wind_speed_mps=MAX_WIND_MPS, wind_speed_threshold_knots=MAX_WIND_THRESH_KN, wind_direction_deg=359,
        ), settings()))
        s = parsed.surf
        assert s.get_wave_period() == MAX_PERIOD
        assert s.get_wave_height() == MAX_HEIGHT_CM
        assert s.get_wave_threshold() == MAX_WAVE_THRESH_CM
        assert s.get_wind_speed() == MAX_WIND_MPS
        assert s.get_wind_threshold() == MAX_WIND_THRESH_KN
        assert s.get_wind_direction() == 359


@pytest.mark.unit
class TestOverflowSaturates:
    """Values wider than their wire field must clamp to the field maximum,
    never wrap. Wrapping turns "impossible" into "very possible":
    the 9999 sentinel the threshold shim sends for "above the user's max"
    would arrive as 9999 mod 128 = 15 knots and make the lamp blink in
    exactly the case it must stay quiet."""

    def test_wave_threshold_sentinel_saturates(self):
        # api_arduino sends IMPOSSIBLE_THRESHOLD (9999 m) * 100 = 999900 cm
        parsed, _ = decode(encode_v3_response_cpp(surf(wave_threshold_cm=999900), settings()))
        assert parsed.surf.get_wave_threshold() == MAX_WAVE_THRESH_CM

    def test_wind_threshold_sentinel_saturates(self):
        parsed, _ = decode(encode_v3_response_cpp(surf(wind_speed_threshold_knots=9999), settings()))
        assert parsed.surf.get_wind_threshold() == MAX_WIND_THRESH_KN

    def test_saturated_threshold_still_exceeds_any_real_reading(self):
        """The whole point of the sentinel: max field value > max field reading."""
        parsed, _ = decode(encode_v3_response_cpp(
            surf(wave_height_cm=MAX_HEIGHT_CM, wave_threshold_cm=999900,
                 wind_speed_mps=MAX_WIND_MPS, wind_speed_threshold_knots=9999),
            settings()))
        s = parsed.surf
        assert s.get_wave_threshold() >= s.get_wave_height()
        # firmware compares wind in knots: mps * 1.944 vs threshold knots.
        # A saturated 127 kn threshold is above any plausible wind; a wrapped
        # 15 kn is not. Assert the decoded value is the field max, not 15.
        assert s.get_wind_threshold() == MAX_WIND_THRESH_KN

    @pytest.mark.parametrize("field,getter,maximum", [
        ("wave_period_s", "get_wave_period", MAX_PERIOD),
        ("wave_height_cm", "get_wave_height", MAX_HEIGHT_CM),
        ("wind_speed_mps", "get_wind_speed", MAX_WIND_MPS),
        ("wind_direction_deg", "get_wind_direction", MAX_DIRECTION),
    ])
    def test_readings_saturate_not_wrap(self, field, getter, maximum):
        parsed, _ = decode(encode_v3_response_cpp(surf(**{field: maximum + 1}), settings()))
        assert getattr(parsed.surf, getter)() == maximum

    def test_negative_reading_clamps_to_zero(self):
        parsed, _ = decode(encode_v3_response_cpp(surf(wave_height_cm=-5, wind_speed_mps=-1), settings()))
        assert parsed.surf.get_wave_height() == 0
        assert parsed.surf.get_wind_speed() == 0


@pytest.mark.unit
class TestSettingsRoundTrip:
    def test_roundtrip_settings_fields(self):
        parsed, _ = decode(encode_v3_response_cpp(surf(), settings()))
        st = parsed.settings
        assert st.get_led_theme() == message_wrapper.LEDTheme.CLASSIC_SURF
        assert st.get_brightness() == 30
        assert st.get_fetch_interval_ms() == 13 * 60 * 1000
        assert st.get_latitude() == pytest.approx(32.4425, abs=1e-4)
        assert st.get_longitude() == pytest.approx(34.8683, abs=1e-4)
        assert st.get_tz_offset() == 7200

    def test_negative_coordinates_and_tz_offset(self):
        """Fixed-point is value*10000 truncated toward zero after a float32
        round-trip, so negatives can lose up to one unit (0.0001 deg, ~11 m).
        Tolerance is two units to stay clear of that edge."""
        parsed, _ = decode(encode_v3_response_cpp(surf(), settings(latitude=-33.8688, longitude=-70.6693, tz_offset=-18000)))
        st = parsed.settings
        assert st.get_latitude() == pytest.approx(-33.8688, abs=2e-4)
        assert st.get_longitude() == pytest.approx(-70.6693, abs=2e-4)
        assert st.get_tz_offset() == -18000

    def test_coordinate_extremes(self):
        parsed, _ = decode(encode_v3_response_cpp(surf(), settings(latitude=-90.0, longitude=180.0)))
        assert parsed.settings.get_latitude() == pytest.approx(-90.0, abs=1e-4)
        assert parsed.settings.get_longitude() == pytest.approx(180.0, abs=1e-4)

    def test_every_brightness_level_encodes_exactly(self):
        """int(x * 100) truncates; the three configured levels must not lose 1%."""
        for name, level in BRIGHTNESS_LEVELS.items():
            parsed, _ = decode(encode_v3_response_cpp(surf(), settings(brightness_multiplier=level)))
            assert parsed.settings.get_brightness() == round(level * 100), name

    def test_fetch_interval_max_20_bits(self):
        parsed, _ = decode(encode_v3_response_cpp(surf(), settings(fetch_interval_ms=MAX_INTERVAL_MS)))
        assert parsed.settings.get_fetch_interval_ms() == MAX_INTERVAL_MS

    def test_fetch_interval_above_field_max_saturates(self):
        """The 20-bit field holds at most 1,048,575 ms (~17.5 min). The server
        allows intervals up to 60 min, so a long interval must saturate to the
        field max, never wrap: 20 min masked would become ~2.5 min and make the
        lamp poll far faster than the user asked. Widening the field is a
        protocol change on both sides; until then saturation is the safe edge."""
        parsed, _ = decode(encode_v3_response_cpp(surf(), settings(fetch_interval_ms=3_600_000)))
        assert parsed.settings.get_fetch_interval_ms() == MAX_INTERVAL_MS
        parsed, _ = decode(encode_v3_response_cpp(surf(), settings(fetch_interval_ms=20 * 60 * 1000)))
        assert parsed.settings.get_fetch_interval_ms() == MAX_INTERVAL_MS


@pytest.mark.unit
class TestThemes:
    KNOWN = ["classic_surf", "vibrant_mix", "tropical_paradise", "ocean_sunset", "electric_vibes"]

    def test_theme_name_to_enum_all_known_distinct(self):
        enums = [theme_to_enum(n) for n in self.KNOWN]
        assert len(set(int(e) for e in enums)) == len(self.KNOWN)

    def test_theme_roundtrip_through_packet(self):
        for name in self.KNOWN:
            parsed, _ = decode(encode_v3_response_cpp(surf(), settings(led_theme=name)))
            assert parsed.settings.get_led_theme() == theme_to_enum(name), name

    def test_unknown_theme_falls_back_to_classic(self):
        assert theme_to_enum("no-such-theme") == message_wrapper.LEDTheme.CLASSIC_SURF
        assert theme_to_enum("") == message_wrapper.LEDTheme.CLASSIC_SURF

    def test_theme_lists_agree_with_user_api(self):
        """One telling: the encoder's known names are exactly the names the
        settings API accepts, and the wire enum has exactly that many values."""
        import inspect
        import blueprints.api_user as api_user
        src = inspect.getsource(api_user.update_led_theme)
        for name in self.KNOWN:
            assert f"'{name}'" in src, name
        assert len(self.KNOWN) == max(int(t) for t in message_wrapper.LEDTheme.__members__.values()) + 1


@pytest.mark.unit
class TestCorruption:
    @pytest.mark.parametrize("byte_index", [0, 3, 7, 9, 16, 24])
    def test_flipped_bit_in_data_fails_crc(self, byte_index):
        packet = bytearray(encode_v3_response_cpp(surf(), settings()))
        packet[byte_index] ^= 0x10
        parsed, handler = decode(bytes(packet))
        assert parsed is None
        assert handler.get_validation_failures() == 1

    @pytest.mark.parametrize("crc_index", [8, 25])
    def test_corrupted_crc_byte_fails(self, crc_index):
        packet = bytearray(encode_v3_response_cpp(surf(), settings()))
        packet[crc_index] ^= 0x01
        parsed, _ = decode(bytes(packet))
        assert parsed is None

    @pytest.mark.parametrize("length", [0, 25, 27])
    def test_wrong_length_rejected(self, length):
        parsed, handler = decode(bytes(length))
        assert parsed is None
        assert handler.get_validation_failures() == 1
