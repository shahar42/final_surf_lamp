"""
Unit tests for web_and_database/locations/beaches.py

beaches.py is the single source of truth for every location in the system:
the processor's API URLs, the registration dropdown, the timezone table and
the coordinate table are all derived from it. A malformed row here breaks
every layer at once, so the data itself is under test, not only the helpers.
"""

import pytest

from locations.beaches import (
    ALL_BEACHES,
    get_all_beaches,
    get_all_beach_names,
    get_beach_by_name,
    search_beaches,
)

REQUIRED_FIELDS = {"english_name", "hebrew_name", "latitude", "longitude", "region", "country", "tags"}


@pytest.mark.unit
class TestBeachData:
    def test_every_beach_has_required_fields(self):
        for beach in get_all_beaches():
            missing = REQUIRED_FIELDS - set(beach)
            assert not missing, f"{beach.get('english_name')} missing {missing}"
            assert beach["english_name"].strip(), "empty english_name"
            assert isinstance(beach["tags"], list) and beach["tags"], f"{beach['english_name']} has no tags"

    def test_beach_names_unique(self):
        names = get_all_beach_names()
        dupes = {n for n in names if names.count(n) > 1}
        assert not dupes, f"duplicate beach names: {dupes}"

    def test_beach_names_unique_case_insensitive(self):
        """get_beach_by_name falls back to a case-insensitive scan, so two names
        differing only by case would make lookups ambiguous."""
        lowered = [n.lower() for n in get_all_beach_names()]
        assert len(lowered) == len(set(lowered))

    def test_coordinates_in_valid_range(self):
        for beach in get_all_beaches():
            assert -90 <= beach["latitude"] <= 90, beach["english_name"]
            assert -180 <= beach["longitude"] <= 180, beach["english_name"]

    def test_get_all_beach_names_matches_all_beaches(self):
        assert get_all_beach_names() == [b["english_name"] for b in ALL_BEACHES]


@pytest.mark.unit
class TestGetBeachByName:
    def test_exact_match(self):
        assert get_beach_by_name("Sdot Yam")["english_name"] == "Sdot Yam"

    def test_case_insensitive_fallback(self):
        assert get_beach_by_name("sdot yam")["english_name"] == "Sdot Yam"
        assert get_beach_by_name("HILTON BEACH (TEL AVIV)")["english_name"] == "Hilton Beach (Tel Aviv)"

    def test_whitespace_is_not_tolerated(self):
        """Documented current behaviour: callers must pass a trimmed name."""
        assert get_beach_by_name(" Sdot Yam") is None

    def test_unknown_returns_none(self):
        assert get_beach_by_name("Atlantis") is None
        assert get_beach_by_name("") is None


@pytest.mark.unit
class TestSearchBeaches:
    def test_prefix_ranks_before_contains(self):
        # "Bat Galim (Haifa)" starts with "bat"; "Backdoor (Haifa)" does not
        # contain "bat" at all, so only prefix logic decides the first hit.
        results = search_beaches("Bat")
        assert results[0]["english_name"] == "Bat Galim (Haifa)"

    def test_contains_match_on_english_name(self):
        names = [b["english_name"] for b in search_beaches("Netanya", limit=50)]
        assert "Kontiki Beach (Netanya)" in names
        assert "Sironit Beach (Netanya)" in names

    def test_tag_match_finds_region_beaches(self):
        names = [b["english_name"] for b in search_beaches("North Coast", limit=50)]
        assert "Bat Galim (Haifa)" in names
        assert "Sdot Yam" not in names  # Central Coast

    def test_country_match_returns_every_beach_of_that_country(self):
        israel = [b for b in search_beaches("Israel", limit=100)]
        expected = [b for b in ALL_BEACHES if b["country"] == "Israel"]
        assert len(israel) == len(expected)

    def test_hebrew_name_search(self):
        names = [b["english_name"] for b in search_beaches("שדות ים")]
        assert names == ["Sdot Yam"]

    def test_search_respects_limit(self):
        assert len(search_beaches("Israel", limit=3)) == 3

    def test_empty_query_returns_first_limit_beaches(self):
        assert search_beaches("", limit=4) == ALL_BEACHES[:4]
        assert search_beaches(None, limit=2) == ALL_BEACHES[:2]

    def test_no_duplicates_in_results(self):
        results = search_beaches("Beach", limit=100)
        names = [b["english_name"] for b in results]
        assert len(names) == len(set(names))

    def test_no_match_returns_empty(self):
        assert search_beaches("zzzz-nowhere") == []
