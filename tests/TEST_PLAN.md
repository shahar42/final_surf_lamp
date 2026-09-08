# Surf Lamp Test Plan

Every file below is a test module. One row per test case. The `Pri` column
is the order to implement in: P0 = bugs here reach customers' lamps
directly, P1 = protects a feature, P2 = nice to have.

## Status

| Group | State |
|---|---|
| 1 threshold and hours | implemented |
| 2 caching and Redis | implemented |
| 3 locations, forms, auth helpers | implemented |
| 4 protocol (Python) | implemented, plus `test_protocol_headers_in_sync.py` (not in the original plan) |
| 5 processor unit | implemented except `test_lamp_repository_guards.py` (the whitelist is a function-local; covered by Group 7 instead) |
| 6 web integration | implemented, 13 files |
| 7 processor integration | implemented; `test_processor_heartbeat_upsert` skipped (Postgres `NOW()`); Redis sync SQL is Postgres-only and stays unit-tested with a mocked engine |
| 8 firmware (C++) | implemented: protocol (incl. server parity fixture), LED mapping, MAC-derived ID, jitter, themes. `test_wifi_backoff.cpp` and the four "requires refactor" items still open |
| 9 tools | implemented (read_lamp_id, qr_generator, id_manager) |

Run everything: `esurf/bin/python -m pytest tests -m "not firmware"` then `make -C tests/unit/firmware test`.

Row names in the tables below are the plan; where an implemented test has a
more precise name, the file is authoritative.

### Bugs found while writing tests (all fixed in the same commits)

| Where | What | Test that guards it |
|---|---|---|
| `cpp_encoder.py` | Fields were masked (`& 0x7F`) instead of clamped. The 9999 "impossible threshold" sentinel arrived at the lamp as 9999 mod 128 = **15 knots**, making it blink exactly when it must not. Fetch intervals over ~17.5 min wrapped to a few minutes. | `test_v3_encoder.py::TestOverflowSaturates` |
| `background_processor.py` | `sync_redis_to_database` imported a `SessionLocal` that `lamp_repository` never defined. ImportError swallowed by the outer `except`; Redis heartbeats never reached `arduinos.last_poll_time`. | `test_redis_sync.py::test_sync_reaches_the_database` |
| `utils/sorter.py` | Python fallback sort raised `TypeError` on a location with `wave_height_m = None`. Render's `build.sh` compiles the `.so`, so production normally takes the C path; the fallback runs wherever the build step is skipped (local dev, CI, a failed gcc step). | `test_sorter.py::test_none_height_is_treated_as_zero` |
| `utils/location_cache.py` | Per-user thresholds and hours flags cached per beach (207f0dd). | `test_location_cache.py` |
| `redis_manager.py` | `UnboundLocalError` in fallback; no socket timeouts (207f0dd). | `test_redis_manager.py` |
| `blueprints/notifications.py` | `/notifications/send-test` pushed to every subscriber with **no authentication**. Now `@admin_required`. | `test_notifications.py::TestSendTestEndpoint` |
| `blueprints/api_arduino.py` | `/api/arduino/status` compared an aware Redis timestamp with the naive DB column and returned 500 whenever Redis held a heartbeat. | `test_api_arduino_legacy.py::TestStatusOverview` |
| `blueprints/api_arduino.py` | Callback with a non-JSON body returned 500 (Flask 415) instead of 400. `get_json(silent=True)`. | `test_api_arduino_legacy.py::test_callback_no_json_400` |
| `blueprints/api_user.py` | Off-times accepted raw `"HH:MM"` strings into a `Time` column (worked on Postgres by coercion, would 500 on bad input). Parsed and validated, 400 on garbage. | `test_api_user.py::TestOffTimes` |
| `tools/manufacturing/id_manager.py` | Every query hit a `lamps` table that has not existed since the schema refactor (`arduinos`). | `test_id_manager.py` |

### Discrepancies pinned, not fixed (need a product decision)

- `admin.get_device_status` uses 15/60 min cutoffs; `shared_config` says 1 h / 24 h. Two tellings of "online".
- Firmware `Themes.cpp` has a 6th theme `dark` (index 5); the V3 enum carries 0-4, so `dark` reaches V3 lamps as `classic_surf`.
- `helpers.get_coordinates_cached` silently falls back to Tel Aviv for unknown locations.
- `/api/admin/arduino-status` is `login_required` only, not `admin_required`, despite the prefix.
- When every wind source fails in a cycle, the processor writes `wind_speed_mps = 0` instead of keeping the previous reading (`test_wind_failure_zeroes_wind_fields_current_behaviour`).
- CSRF is per-form (FlaskForm); JSON endpoints rely on the `SameSite=Lax` session cookie, no `CSRFProtect`.
- `add_user_and_lamp` maps IntegrityErrors to messages by Postgres constraint names (`users_email_key`); on any other backend duplicates report the generic "Registration failed".

Layout:

```
tests/
  unit/           pure logic, no network, no DB, no Redis. Milliseconds.
    web/          web_and_database/ helpers and utilities
    protocol/     V3 binary protocol (Python side)
    processor/    surf-lamp-processor/ pure functions
    firmware/     C++ compiled natively with g++ + tiny Arduino shim
    tools/        tools/manufacturing/
  integration/    Flask test client + SQLite + fake Redis. Seconds.
    web/          one file per blueprint
    processor/    process_all_lamps against SQLite with mocked HTTP
  fixtures/       sample API payloads, factory helpers
  simulator/      virtual lamp (deferred, see bottom)
```

Infrastructure needed before any test runs (not tests, listed for completeness):

| Item | Why |
|---|---|
| Fix `.gitignore` lines 112-114 | Currently ignores `test_*.py`, `*_test.py`, `test_system/`. This is why no test survived. |
| `pytest.ini` at repo root | `testpaths = tests`, markers `unit` / `integration` / `firmware`, `pythonpath` for the three service dirs. |
| `tests/conftest.py` | Sets `SECRET_KEY`, unsets `REDIS_URL`, provides `fake_redis`, `app`, `client`, `db_session` (SQLite in-memory), `freeze_time`. |
| `requirements-dev.txt` | pytest, pytest-cov, fakeredis, freezegun, responses. |
| `.githooks/pre-push` + `git config core.hooksPath .githooks` | Runs `pytest -m "not firmware"` before every push. Versioned, unlike `.git/hooks`. |
| `.github/workflows/tests.yml` | Same command on push and PR. Firmware job compiles `tests/unit/firmware` with g++. |
| Delete `test_system/`, `surf-lamp-processor/test_*.py`, `web_and_database/test_*.py` | All broken. Intent is ported into the rows below. |

---

## Group 1: unit/web — threshold and hours logic (P0)

These decide what every lamp shows. A bug here is visible on the strip.

### `tests/unit/web/test_threshold_logic.py`
`web_and_database/utils/threshold_logic.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_below_min_returns_min` | current < min -> threshold == min (lamp does not blink) |
| P0 | `test_inside_range_returns_min` | min <= current <= max -> threshold == min (lamp blinks) |
| P0 | `test_above_max_returns_impossible` | current > max -> threshold == 9999 sentinel (lamp does not blink) |
| P0 | `test_no_max_behaves_as_simple_threshold` | user_max None -> threshold == min always |
| P0 | `test_current_none_returns_min` | no surf data yet -> min, never crashes |
| P1 | `test_boundary_equal_to_max_blinks` | current == max is inside range |
| P1 | `test_boundary_equal_to_min_blinks` | current == min is inside range |
| P1 | `test_validate_range_rejects_min_above_max` | `validate_threshold_range` |
| P1 | `test_validate_range_accepts_equal_min_max` | |
| P2 | `test_validate_range_rejects_negative` | |

### `tests/unit/web/test_hours.py`
`web_and_database/utils/helpers.py` : `is_quiet_hours`, `is_off_hours`, `get_current_tz_offset`. All use `freezegun`.

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_quiet_hours_overnight_window_inside` | 23:00 local -> True with default 22-06 |
| P0 | `test_quiet_hours_overnight_window_outside` | 12:00 local -> False |
| P0 | `test_quiet_hours_boundary_start_inclusive` | 22:00 -> True |
| P0 | `test_quiet_hours_boundary_end_exclusive` | 06:00 -> False |
| P0 | `test_quiet_hours_disabled_flag_wins` | enabled=False -> False even at 23:00 |
| P0 | `test_quiet_hours_unknown_location_false` | location not in LOCATION_TIMEZONES -> False |
| P0 | `test_off_hours_overnight_window` | start 22:00, end 06:00, now 02:00 -> True |
| P0 | `test_off_hours_same_day_window` | start 13:00, end 15:00, now 14:00 -> True; 16:00 -> False |
| P0 | `test_off_hours_disabled_or_missing_times_false` | enabled=False, or start/end None -> False |
| P0 | `test_off_hours_uses_location_timezone_not_server` | same UTC instant, two locations, different answers |
| P1 | `test_off_hours_priority_over_quiet_hours_in_endpoint` | belongs in integration; cross-ref Group 6 |
| P1 | `test_tz_offset_summer_vs_winter` | Israel: 3 in July, 2 in January |
| P1 | `test_tz_offset_unknown_location_defaults_to_2` | |
| P2 | `test_quiet_hours_custom_window_same_day` | start 9, end 17 |

### `tests/unit/web/test_helpers_misc.py`
`helpers.py` : `convert_wind_direction`, `get_sunset_info_cached`, `get_coordinates_cached`, `invalidate_user_coordinates_cache`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_wind_direction_cardinal_points` | 0->N, 90->E, 180->S, 270->W, 360->N |
| P1 | `test_wind_direction_boundaries` | 22.5 rounding behaviour at each sector edge |
| P1 | `test_sunset_cache_hit_within_24h` | second call does not invoke get_sunset_func |
| P1 | `test_sunset_cache_expires_after_24h` | freezegun tick 24h+1s -> recomputed |
| P1 | `test_coordinates_cache_keyed_per_user` | two users, same location, separate entries |
| P1 | `test_coordinates_cache_invalidated_on_location_change` | cached_location != new location -> refetch |
| P1 | `test_coordinates_cache_manual_invalidate` | |
| P2 | `test_coordinates_unknown_location_falls_back_to_default` | |

---

## Group 2: unit/web — caching and Redis (P0, protects today's fixes)

### `tests/unit/web/test_location_cache.py`
`web_and_database/utils/location_cache.py` (uses `fakeredis`)

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_two_users_same_beach_get_own_thresholds` | regression for the cache leak fixed in 207f0dd |
| P0 | `test_two_users_same_beach_get_own_hours_flags` | quiet/off flags not shared |
| P0 | `test_cached_blob_contains_only_location_fields` | no threshold or hours keys in Redis value |
| P0 | `test_second_call_is_cache_hit` | cache_hit False then True |
| P0 | `test_ttl_is_60_seconds` | fakeredis TTL check |
| P0 | `test_redis_down_returns_data_uncached` | fake raising client -> data returned, cache_hit False, no exception |
| P1 | `test_key_prefix_is_v4` | old v3 blob present -> ignored |
| P1 | `test_stale_warning_uses_threshold_constant` | consecutive_identical > STALE_DATA_THRESHOLD |
| P1 | `test_data_available_false_when_both_zero` | |
| P1 | `test_none_fields_become_zero` | Location with None wave/wind |
| P2 | `test_get_location_stats_strips_prefix` | |
| P1 | `test_db_location_cache_ttl_and_invalidate` | `get_location_from_db_cached`, `invalidate_db_location_cache` |

### `tests/unit/web/test_redis_manager.py`
`web_and_database/redis_manager.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_record_db_write_no_redis_does_not_raise` | regression for UnboundLocalError |
| P0 | `test_client_has_socket_timeouts` | from_url called with 2s connect and socket timeout |
| P0 | `test_unreachable_redis_fails_within_3s` | real client to 10.255.255.1, measure |
| P0 | `test_no_redis_url_returns_none` | |
| P1 | `test_can_write_to_db_redis_nx_semantics` | first True, second within cooldown False |
| P1 | `test_can_write_to_db_fallback_sampling` | seed random, ~10% pass |
| P1 | `test_fallback_history_cleanup_over_1000` | old entries pruned |
| P1 | `test_fallback_history_capped_at_5000` | |
| P2 | `test_record_redis_health_success_resets_failures` | mocked session |
| P2 | `test_record_redis_health_unhealthy_after_3_failures` | |

### `tests/unit/web/test_rate_limit.py`
`web_and_database/utils/rate_limit.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_ten_changes_allowed_eleventh_blocked` | |
| P1 | `test_counter_resets_at_local_midnight` | freezegun |
| P2 | `test_users_are_independent` | |

---

## Group 3: unit/web — locations, forms, auth helpers (P1)

### `tests/unit/web/test_beaches.py`
`web_and_database/locations/beaches.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_every_beach_has_required_fields` | english_name, latitude, longitude, timezone |
| P1 | `test_beach_names_unique` | |
| P1 | `test_coordinates_in_valid_range` | -90..90, -180..180 |
| P1 | `test_get_beach_by_name_case_and_whitespace` | |
| P1 | `test_search_prefix_and_substring` | |
| P1 | `test_search_respects_limit` | |
| P2 | `test_search_hebrew_names` | if hebrew_name field exists |

### `tests/unit/web/test_beach_service.py`
`web_and_database/locations/beach_service.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_wave_url_contains_marine_api_and_coords` | |
| P1 | `test_wind_url_contains_forecast_api_and_coords` | |
| P1 | `test_wind_url_uses_utc_timezone_param` | regression for 469c752 |
| P1 | `test_owm_url_none_without_api_key` | env unset |
| P1 | `test_owm_url_with_api_key` | key present in query |
| P1 | `test_get_api_urls_unknown_beach_none` | |
| P2 | `test_is_valid_beach` | |

### `tests/unit/web/test_shared_config.py`
`shared_config.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_every_location_has_wave_and_wind_source` | `get_api_sources_for_location` |
| P0 | `test_wind_sources_ordered_open_meteo_then_owm` | priority 1 then 2 when key set |
| P1 | `test_wind_sources_only_open_meteo_without_key` | |
| P1 | `test_unknown_location_returns_empty_sources` | |
| P1 | `test_wave_calculation_method_default_api` | |
| P1 | `test_location_endpoints_json_overrides_fallback` | temp json file |
| P2 | `test_interval_sql_helpers` | |

### `tests/unit/web/test_forms.py`
`web_and_database/forms.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_registration_arduino_id_max_16777215` | MAC-derived upper bound |
| P0 | `test_registration_arduino_id_rejects_zero_and_over_max` | |
| P1 | `test_sanitize_strips_html_and_scripts` | |
| P1 | `test_sanitized_field_trims_whitespace` | |
| P1 | `test_password_length_bounds_from_security_config` | |
| P1 | `test_location_must_be_valid_beach` | |
| P2 | `test_email_normalised_lowercase` | |

### `tests/unit/web/test_auth_helpers.py`
`web_and_database/blueprints/auth.py` : `_validate_arduino_id_from_qr`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_qr_id_accepts_legacy_small_id` | 14 |
| P0 | `test_qr_id_accepts_max_24bit` | 16777215 |
| P0 | `test_qr_id_rejects_zero_negative_overflow` | 0, -1, 16777216 |
| P0 | `test_qr_id_rejects_non_numeric` | "abc", None, "" |

### `tests/unit/web/test_admin_helpers.py`
`web_and_database/blueprints/admin.py` : `get_device_status`, `get_broadcast_expiry`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_status_active_under_1h` | uses shared_config thresholds |
| P1 | `test_status_stale_between_1h_and_24h` | |
| P1 | `test_status_offline_over_24h` | |
| P1 | `test_status_never_when_null` | |
| P1 | `test_status_handles_naive_and_aware_datetimes` | |
| P2 | `test_broadcast_expiry_options` | |

### `tests/unit/web/test_query_result.py`
`web_and_database/models/query_result.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_properties_default_none_to_zero` | |
| P1 | `test_is_stale_threshold` | |

### `tests/unit/web/test_sorter.py`
`web_and_database/utils/sorter.py`

| Pri | Test | Asserts |
|---|---|---|
| P2 | `test_sort_descending_by_height` | |
| P2 | `test_python_fallback_matches_c_sort` | when .so present |
| P2 | `test_empty_and_single` | |

---

## Group 4: unit/protocol — V3 binary protocol, Python side (P0)

### `tests/unit/protocol/test_v3_encoder.py`
`cpp_message_wrapper/cpp_encoder.py` + `message_wrapper` extension

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_output_is_exactly_26_bytes` | |
| P0 | `test_roundtrip_surf_fields` | encode then parse with MessageHandler, every field equal |
| P0 | `test_roundtrip_settings_fields` | theme, brightness, interval, lat, lon, tz |
| P0 | `test_surf_crc_valid` | byte 8 |
| P0 | `test_settings_crc_valid` | byte 25 |
| P0 | `test_flags_independent` | stale, data_available, quiet, off each toggled alone |
| P0 | `test_threshold_sentinel_9999_fits` | 9999 cm survives the field width |
| P1 | `test_field_max_values_clamp_not_wrap` | wave 65535 cm, wind 255, direction 359 |
| P1 | `test_negative_tz_offset` | |
| P1 | `test_theme_name_to_enum_all_known` | every Themes.cpp name |
| P1 | `test_unknown_theme_falls_back` | |
| P1 | `test_corrupted_byte_fails_crc` | flip one bit -> parse rejects |
| P2 | `test_brightness_percent_rounding` | 0.5 -> 50 |

### `tests/unit/protocol/test_crc8.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_known_vectors_poly_0x07` | standard CRC-8 check values |
| P0 | `test_python_reference_matches_extension` | pure-Python CRC vs C++ |

---

## Group 5: unit/processor (P0/P1)

### `tests/unit/processor/test_surf_data_transformer.py`
Uses fixtures in `tests/fixtures/api_responses/` (open-meteo marine, open-meteo forecast, isramar, openweathermap).

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_open_meteo_marine_standardizes` | wave_height_m, wave_period_s |
| P0 | `test_open_meteo_forecast_wind_standardizes` | wind_speed_mps, wind_direction_deg |
| P0 | `test_openweathermap_wind_standardizes` | new fallback source |
| P0 | `test_current_hour_index_utc` | regression for 469c752 |
| P0 | `test_current_hour_index_missing_hour_falls_back` | |
| P1 | `test_extract_field_nested_path` | `a.b[0].c` |
| P1 | `test_extract_field_missing_returns_none` | |
| P1 | `test_apply_conversions_kmh_to_mps` | |
| P1 | `test_calculate_wave_from_wind_formula` | |
| P1 | `test_normalize_low_values` | |
| P1 | `test_isramar_extractor` | |
| P2 | `test_unknown_endpoint_url_returns_none` | |

### `tests/unit/processor/test_endpoint_configs.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_get_endpoint_config_matches_by_host` | |
| P1 | `test_every_config_has_required_mapping_keys` | |
| P1 | `test_wave_calculation_config_known_methods` | |

### `tests/unit/processor/test_weather_api_client.py`
`responses` library to mock HTTP.

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_fallback_tries_priority_order` | 1 fails -> 2 called |
| P0 | `test_first_success_stops_chain` | 2 never called |
| P0 | `test_all_fail_returns_none_not_raise` | |
| P1 | `test_timeout_counts_as_failure` | |
| P1 | `test_non_200_counts_as_failure` | |
| P1 | `test_malformed_json_counts_as_failure` | |

### `tests/unit/processor/test_staleness.py`
`background_processor.is_data_identical`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_identical_within_float_tolerance` | |
| P0 | `test_different_wave_height_not_identical` | |
| P0 | `test_missing_old_data_not_identical` | first run |
| P1 | `test_none_vs_zero` | |

### `tests/unit/processor/test_redis_sync.py`
`background_processor.sync_redis_to_database` with mocked engine and fakeredis.

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_bulk_update_sql_only_advances_newer` | WHERE clause present |
| P0 | `test_batches_of_1000` | 2500 entries -> 3 executes |
| P1 | `test_invalid_timestamp_skipped_not_fatal` | |
| P1 | `test_no_redis_returns_false` | |
| P1 | `test_ids_are_ints_not_interpolated_strings` | injection guard |

### `tests/unit/processor/test_lamp_repository_guards.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_allowed_tables_whitelist_rejects_unknown` | |

### `tests/unit/processor/test_sunset_calculator.py`
Server side still serves V1.

| Pri | Test | Asserts |
|---|---|---|
| P2 | `test_trigger_inside_window` | freezegun |
| P2 | `test_trigger_outside_window` | |
| P2 | `test_unknown_location_default_coords` | |

---

## Group 6: integration/web — Flask app (P0)

Fixtures: `app` with SQLite, `fake_redis`, factory helpers `make_user`, `make_arduino`, `make_location`. Every request as the lamp sends header `User-Agent: ESP32HTTPClient`.

### `tests/integration/web/test_api_arduino_v3.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_v3_returns_26_bytes_octet_stream` | |
| P0 | `test_v3_unknown_arduino_404` | |
| P0 | `test_v3_off_hours_flag_set` | freezegun inside user off window |
| P0 | `test_v3_off_hours_wins_over_quiet_hours` | both true -> off flag true (priority rule) |
| P0 | `test_v3_quiet_hours_forces_mid_brightness` | |
| P0 | `test_v3_threshold_shim_above_max_sends_9999` | end to end |
| P0 | `test_v3_two_lamps_same_beach_different_owners` | decoded thresholds differ (cache leak, end to end) |
| P0 | `test_v3_physical_ua_records_heartbeat` | fake_redis hash updated |
| P0 | `test_v3_dashboard_ua_does_not_record_heartbeat` | |
| P0 | `test_v3_fetch_interval_min_7_minutes` | |
| P1 | `test_v3_stale_warning_from_consecutive_updates` | |
| P1 | `test_v3_data_available_false_when_no_conditions` | |
| P1 | `test_v3_redis_down_still_returns_200` | fake raising client |
| P1 | `test_v3_mac_derived_large_id_works` | id 16777215 |

### `tests/integration/web/test_api_arduino_legacy.py`
V1, V2, callback, status.

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_v2_json_has_coordinates_and_tz` | |
| P1 | `test_v1_json_has_sunset_fields` | |
| P1 | `test_callback_updates_heartbeat` | |
| P1 | `test_callback_missing_id_400` | |
| P1 | `test_callback_unknown_id_404` | |
| P1 | `test_status_overview_merges_redis_timestamps` | |
| P2 | `test_discovery_endpoint_returns_host` | |

### `tests/integration/web/test_auth_flow.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_register_requires_qr_id` | GET /register without id -> error |
| P0 | `test_register_creates_user_arduino_location` | three rows |
| P0 | `test_register_duplicate_arduino_id_rejected` | |
| P0 | `test_register_accepts_24bit_id` | |
| P0 | `test_register_rejects_id_over_max` | |
| P1 | `test_login_success_sets_session` | |
| P1 | `test_login_wrong_password` | |
| P1 | `test_logout_clears_session` | |
| P1 | `test_forgot_password_generic_message_for_unknown_email` | no enumeration |
| P1 | `test_reset_token_expires_20_minutes` | |
| P1 | `test_reset_token_single_use` | |
| P1 | `test_new_reset_request_invalidates_old_token` | |
| P2 | `test_login_rate_limit_10_per_minute` | |

### `tests/integration/web/test_dashboard.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_add_arduino_links_to_current_user` | |
| P0 | `test_add_arduino_rejects_out_of_range` | regression for 9790cc8 guard |
| P0 | `test_add_arduino_returns_json_not_500` | regression for 321e621 jsonify |
| P1 | `test_dashboard_requires_login` | |
| P1 | `test_dashboard_hides_stale_conditions` | regression for 56f8803 |
| P2 | `test_wifi_guide_renders_markdown` | |

### `tests/integration/web/test_api_user.py`
One test per endpoint for happy path, one for validation, one for auth.

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_update_threshold_persists_min_max` | |
| P0 | `test_update_threshold_rejects_min_above_max` | |
| P0 | `test_update_wind_threshold_persists` | |
| P0 | `test_update_off_times_persists_and_enables` | |
| P0 | `test_update_location_cascades_to_arduinos` | 1:N rule |
| P0 | `test_update_location_invalidates_coordinate_cache` | |
| P1 | `test_update_location_rejects_unknown_beach` | |
| P1 | `test_update_location_daily_limit` | |
| P1 | `test_update_brightness_only_known_levels` | |
| P1 | `test_update_led_theme_only_known_themes` | |
| P1 | `test_toggle_quiet_hours` | |
| P1 | `test_update_unit_preference` | |
| P1 | `test_all_endpoints_require_login` | parametrized |
| P2 | `test_all_endpoints_require_csrf` | parametrized |

### `tests/integration/web/test_api_locations.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_public_conditions_no_auth` | |
| P1 | `test_public_conditions_cache_control_header` | |
| P1 | `test_public_conditions_unknown_404` | |
| P1 | `test_public_conditions_no_user_fields` | privacy |

### `tests/integration/web/test_api_beaches.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_search_returns_matches` | |
| P1 | `test_search_empty_query` | |
| P2 | `test_list_all` | |

### `tests/integration/web/test_api_health.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_health_reports_db_redis_processor` | |
| P1 | `test_health_degraded_when_redis_down` | |
| P1 | `test_health_processor_stale_heartbeat` | |

### `tests/integration/web/test_admin.py`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_admin_routes_require_admin` | parametrized over every admin route |
| P1 | `test_create_broadcast_deactivates_previous` | |
| P1 | `test_broadcast_dismiss_hides_for_user_only` | |
| P1 | `test_arduino_status_api_merges_redis` | |
| P1 | `test_admin_stats_only_locations_with_arduinos` | regression for 33e45aa |
| P2 | `test_broadcast_rate_limit` | |

### `tests/integration/web/test_notifications.py`
`webpush` mocked.

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_subscribe_stores_subscription` | |
| P1 | `test_subscribe_idempotent_same_endpoint` | |
| P1 | `test_push_broadcast_filters_by_location` | |
| P1 | `test_push_410_deletes_subscription` | |
| P1 | `test_push_403_404_delete_too` | |
| P1 | `test_push_other_error_keeps_subscription` | |
| P2 | `test_vapid_public_key_endpoint` | |

### `tests/integration/web/test_reports.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_report_error_persists` | |
| P1 | `test_report_error_requires_login` | |
| P2 | `test_report_error_rate_limit` | |

### `tests/integration/web/test_landing_waitlist.py`
Google Sheets REST mocked with `responses`.

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_waitlist_submit_appends_row` | |
| P1 | `test_waitlist_submit_sends_confirmation_email` | mail mocked |
| P1 | `test_waitlist_duplicate_email` | |
| P1 | `test_waitlist_rate_limit_3_per_hour` | |
| P2 | `test_landing_static_routes` | |

### `tests/integration/web/test_security.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_security_headers_present` | CSP, X-Frame-Options, etc. |
| P1 | `test_csrf_rejects_missing_token_on_forms` | |
| P1 | `test_login_required_redirects` | |
| P1 | `test_admin_required_403_for_normal_user` | |
| P2 | `test_proxyfix_uses_first_forwarded_ip` | |

---

## Group 7: integration/processor (P0)

### `tests/integration/processor/test_process_all_lamps.py`
SQLite engine, `responses` for HTTP, fixtures for API payloads.

| Pri | Test | Asserts |
|---|---|---|
| P0 | `test_one_wave_fetch_per_active_location` | |
| P0 | `test_shared_wind_fetched_once_per_cycle` | current Israel-only behaviour; delete when reverted |
| P0 | `test_wind_fallback_to_owm_when_open_meteo_fails` | |
| P0 | `test_identical_data_increments_counter_keeps_timestamp` | |
| P0 | `test_changed_data_resets_counter_updates_timestamp` | |
| P0 | `test_location_without_arduinos_skipped` | |
| P0 | `test_wave_fetch_failure_skips_location_not_cycle` | |
| P1 | `test_wind_failure_still_updates_wave` | |
| P1 | `test_upsert_creates_missing_location_row_with_urls` | |
| P1 | `test_heartbeat_written_each_minute` | |
| P1 | `test_cycle_returns_false_on_db_error` | |

### `tests/integration/processor/test_lamp_repository.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_get_active_locations_distinct` | |
| P1 | `test_update_location_conditions_upsert` | |
| P1 | `test_get_current_location_values` | |
| P1 | `test_processor_heartbeat_upsert` | |

---

## Group 8: unit/firmware — C++ compiled natively (P0 for protocol, P1 rest)

Compiled with `g++ -std=c++17` against a tiny `tests/unit/firmware/shim/Arduino.h`
that provides `millis()`, `Serial`, `ESP.getEfuseMac()`, and `CRGB`/`CHSV` stubs.
Only headers that are already Arduino-free or can be shimmed are included. Files that
pull in FastLED rendering or WiFi are out of scope until their logic is extracted.

### `tests/unit/firmware/test_protocol.cpp`
`esp_Server_encoding.hpp`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `pack_unpack_surf_roundtrip` | every getter returns what PackData was given |
| P0 | `pack_unpack_settings_roundtrip` | |
| P0 | `crc8_known_vectors` | same vectors as Python test |
| P0 | `parity_with_python_encoder` | reads 26 bytes produced by cpp_encoder from a fixture file, decodes, compares. This is the server-to-lamp contract check. |
| P0 | `corrupted_byte_fails_validate` | |
| P1 | `threshold_9999_fits_field` | |
| P1 | `negative_tz_offset_roundtrip` | |

### `tests/unit/firmware/test_led_mapping.cpp`
`Config.h` : `LEDMappingConfig`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `wave_cm_to_led_count_linear_and_clamped` | 0 -> 0, max -> full strip, over max -> full strip |
| P0 | `wind_mps_to_led_count` | |
| P0 | `wave_period_to_led_count` | |
| P0 | `mps_to_knots_conversion` | 1 m/s = 1.944 kn |
| P1 | `threshold_brightness_scaling` | |
| P1 | `strip_direction_auto_detect` | FORWARD macros match BOTTOM/TOP ordering |
| P1 | `static_asserts_compile` | compilation itself is the test |

### `tests/unit/firmware/test_arduino_id.cpp`
`Config.h` : `getArduinoId`

| Pri | Test | Asserts |
|---|---|---|
| P0 | `id_is_low_three_nic_bytes_of_mac` | shim MAC 0x112233445566 -> id == 0x665544? (verify byte order against ESP.getEfuseMac layout) |
| P0 | `id_never_zero` | MAC with zero NIC bytes -> 1 |
| P0 | `id_fits_24_bits` | <= 16777215 |
| P1 | `id_is_cached_after_first_call` | shim counts eFuse reads |

### `tests/unit/firmware/test_jitter.cpp`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `startup_jitter_within_120s` | |
| P1 | `reconnect_jitter_within_60s` | |
| P1 | `interval_shift_within_120s` | |
| P1 | `jitter_deterministic_per_id` | |
| P2 | `jitter_distribution_over_1000_ids` | no bucket > 2x mean |

### `tests/unit/firmware/test_themes.cpp`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `name_to_index_roundtrip_all_themes` | |
| P1 | `unknown_name_falls_back_to_default` | |
| P1 | `theme_indices_match_server_enum` | compare against `esp_Server_encoding.hpp` LEDTheme |

### `tests/unit/firmware/test_wifi_backoff.cpp`
`WiFiHandler.cpp` : `calculateExponentialTimeout`, `calculateExponentialDelay` (need extraction into a header first)

| Pri | Test | Asserts |
|---|---|---|
| P2 | `exponential_capped_at_max` | |
| P2 | `first_attempt_is_initial` | |

### Requires refactor before testable (listed so they are not forgotten)
- `LedController.cpp` threshold decision (`applyWaveHeightThreshold` / `applyWindSpeedThreshold`): the "should blink" decision is fused with FastLED calls. Extract a pure `shouldBlink(current, threshold, quietHours)` and test it.
- `LedController.cpp` priority chain (`updateSurfDisplay`): errors > off hours > quiet hours > normal. Extract a pure `selectDisplayMode(DisplayCache)` returning an enum and test all orderings.
- `WebServerHandler.cpp` `processBinarySurfData`: writes globals directly. Split "decode 26 bytes into a struct" from "apply struct to lastSurfData" and test the first half.
- `Watchdog` : `isAlive` timing is testable if `millis()` is shimmed. P2.

---

## Group 9: unit/tools — manufacturing (P1)

### `tests/unit/tools/test_read_lamp_id.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_id_regex_matches_boot_line` | `"   Arduino ID: 6689108 (decimal)"` |
| P1 | `test_id_regex_ignores_other_lines` | |
| P1 | `test_read_returns_none_on_timeout` | fake serial |
| P1 | `test_port_autodetect_filters_usb_acm` | |

### `tests/unit/tools/test_qr_generator.py`

| Pri | Test | Asserts |
|---|---|---|
| P1 | `test_qr_url_format` | `/register?id=N` |
| P1 | `test_qr_decodes_back_to_id` | pyzbar or qrcode reader if available |
| P2 | `test_print_sheet_grid_dimensions` | |

### `tests/unit/tools/test_id_manager.py` (legacy sequential IDs)

| Pri | Test | Asserts |
|---|---|---|
| P2 | `test_next_id_fills_gaps_or_appends` | mocked DB |
| P2 | `test_is_id_available` | |

---

## Deferred: `tests/simulator/`

A protocol-accurate virtual lamp: polls V3 with the ESP32 user agent, decodes the 26 bytes the way `esp_Server_encoding.hpp` does, checks both CRCs, and asserts per-user fields against the owner's DB row. Would replace the hand-written decode in Group 6 and be runnable against staging. Not in this batch.

---

## Counts

| Group | Files | Cases | P0 |
|---|---|---|---|
| 1 threshold and hours | 3 | 32 | 15 |
| 2 caching and Redis | 3 | 25 | 10 |
| 3 locations, forms, auth | 8 | 43 | 8 |
| 4 protocol (Python) | 2 | 15 | 9 |
| 5 processor unit | 7 | 34 | 13 |
| 6 web integration | 13 | 90 | 25 |
| 7 processor integration | 2 | 15 | 7 |
| 8 firmware (C++) | 6 | 28 | 12 |
| 9 tools | 3 | 9 | 0 |
| **Total** | **47** | **291** | **99** |
