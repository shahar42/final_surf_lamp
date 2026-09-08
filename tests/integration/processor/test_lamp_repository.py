"""Integration tests for surf-lamp-processor/lamp_repository.py against SQLite."""

import pytest

import background_processor
import lamp_repository

from .conftest import location_row


@pytest.mark.integration
class TestConnection:
    def test_database_connection_true_with_schema(self):
        assert lamp_repository.test_database_connection(background_processor.engine) is True

    def test_database_connection_false_when_unreachable(self):
        from sqlalchemy import create_engine
        assert lamp_repository.test_database_connection(create_engine("sqlite:////nonexistent-dir/never.db")) is False


@pytest.mark.integration
class TestQueries:
    def test_get_active_locations_distinct_and_sorted(self, seed, session):
        import data_base
        seed(["Sdot Yam", "Bat Galim (Haifa)"])
        # second arduino at Sdot Yam must not duplicate the location
        user = session.query(data_base.User).first()
        session.add(data_base.Arduino(arduino_id=999, user_id=user.user_id, location="Sdot Yam"))
        session.commit()
        assert lamp_repository.get_active_locations(background_processor.engine) == ["Bat Galim (Haifa)", "Sdot Yam"]

    def test_get_arduinos_for_location(self, seed):
        seed(["Sdot Yam", "Bat Galim (Haifa)"])
        rows = lamp_repository.get_arduinos_for_location(background_processor.engine, "Sdot Yam")
        assert [r["arduino_id"] for r in rows] == [100]
        assert rows[0]["location"] == "Sdot Yam"

    def test_get_current_location_values(self, seed):
        seed(["Sdot Yam"])
        vals = lamp_repository.get_current_location_values(background_processor.engine, "Sdot Yam")
        assert vals["wave_height_m"] == 0.5
        assert vals["consecutive_identical_updates"] == 0
        assert lamp_repository.get_current_location_values(background_processor.engine, "Atlantis") is None

    def test_get_location_api_configs_only_active(self, seed, session):
        import data_base
        seed(["Sdot Yam"])
        session.add(data_base.Location(location="Hilton Beach (Tel Aviv)", wave_api_url="w", wind_api_url="x"))
        session.commit()
        cfg = lamp_repository.get_location_api_configs(background_processor.engine)
        assert set(cfg) == {"Sdot Yam"}
        assert cfg["Sdot Yam"]["wave_calculation_method"] == "api"
        assert cfg["Sdot Yam"]["current_values"]["wave_height_m"] == 0.5


@pytest.mark.integration
class TestUpsert:
    def test_update_location_conditions_inserts_then_updates(self, session):
        data = {"wave_height_m": 1.1, "wave_period_s": 6.0, "wind_speed_mps": 3.0, "wind_direction_deg": 200}
        assert lamp_repository.update_location_conditions(background_processor.engine, "Sdot Yam", data, 0, True) is True
        row = location_row(session, "Sdot Yam")
        assert row.wave_height_m == 1.1
        assert "marine-api.open-meteo.com" in row.wave_api_url

        assert lamp_repository.update_location_conditions(background_processor.engine, "Sdot Yam", {**data, "wave_height_m": 2.2}, 3, False) is True
        row = location_row(session, "Sdot Yam")
        assert row.wave_height_m == 2.2
        assert row.consecutive_identical_updates == 3

    def test_update_location_conditions_missing_fields_default_zero(self, session):
        assert lamp_repository.update_location_conditions(background_processor.engine, "Sdot Yam", {"wave_height_m": 0.9}) is True
        row = location_row(session, "Sdot Yam")
        assert (row.wave_period_s, row.wind_speed_mps, row.wind_direction_deg) == (0.0, 0.0, 0)

    def test_update_location_conditions_unknown_beach_still_writes_with_empty_urls(self, session):
        """No beaches.py entry -> URLs empty strings (NOT NULL satisfied), row still written."""
        assert lamp_repository.update_location_conditions(background_processor.engine, "Atlantis", {"wave_height_m": 1.0}) is True
        row = location_row(session, "Atlantis")
        assert row.wave_api_url == "" and row.wind_api_url == ""

    def test_legacy_threshold_lookups(self, seed, session):
        import data_base
        seed(["Sdot Yam"])
        user = session.query(data_base.User).first()
        user.wave_threshold_m = 1.7
        user.wind_threshold_knots = 18.0
        session.commit()
        assert lamp_repository.get_user_threshold_for_arduino(background_processor.engine, 100) == 1.7
        assert lamp_repository.get_user_wind_threshold_for_arduino(background_processor.engine, 100) == 18.0
        assert lamp_repository.get_user_threshold_for_arduino(background_processor.engine, 999) == 1.0   # default
        assert lamp_repository.get_user_wind_threshold_for_arduino(background_processor.engine, 999) == 22.0

    @pytest.mark.skip(reason="update_processor_heartbeat uses Postgres NOW(); covered by deployment health checks")
    def test_processor_heartbeat_upsert(self):
        pass
