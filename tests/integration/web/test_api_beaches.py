"""Integration tests for the beach autocomplete API."""

import pytest

from locations.beaches import get_all_beaches


@pytest.mark.integration
class TestBeachSearch:
    def test_search_returns_matches(self, client):
        body = client.get("/api/beaches/search?q=Netanya").get_json()
        assert body["success"] is True
        assert body["query"] == "Netanya"
        names = [b["name"] for b in body["beaches"]]
        assert "Kontiki Beach (Netanya)" in names
        assert body["count"] == len(names)

    def test_search_result_shape(self, client):
        beach = client.get("/api/beaches/search?q=Sdot").get_json()["beaches"][0]
        assert set(beach) == {"name", "hebrew_name", "lat", "lng", "region", "country", "tags"}

    def test_search_empty_query_returns_popular(self, client):
        body = client.get("/api/beaches/search?q=&limit=3").get_json()
        assert body["count"] == 3
        assert [b["name"] for b in body["beaches"]] == [b["english_name"] for b in get_all_beaches()[:3]]

    def test_search_limit_capped(self, client):
        body = client.get("/api/beaches/search?q=Israel&limit=999").get_json()
        assert body["count"] <= 27

    def test_search_no_match(self, client):
        body = client.get("/api/beaches/search?q=zzzz").get_json()
        assert body["count"] == 0 and body["beaches"] == []

    def test_list_all(self, client):
        body = client.get("/api/beaches").get_json()
        assert body["count"] == len(get_all_beaches())
