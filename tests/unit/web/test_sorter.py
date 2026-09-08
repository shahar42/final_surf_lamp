"""
Unit tests for web_and_database/utils/sorter.py

The admin stats page sorts locations by wave height through an optional C
merge sort (.so). The Python fallback must give identical results, because
whether the .so exists depends on the build environment, not on the code.
"""

import pytest

from utils import sorter

DATA = [("A", 1.2), ("B", 0.3), ("C", 2.5), ("D", 1.2), ("E", 0.0)]


@pytest.mark.unit
class TestPythonFallback:
    @pytest.fixture(autouse=True)
    def force_python(self, monkeypatch):
        monkeypatch.setattr(sorter, "HAS_LIBSORT", False)

    def test_sort_descending_by_height(self):
        names = [n for n, _ in sorter.sort_by_wave_height(DATA)]
        assert names[0] == "C"
        assert names[-1] == "E"
        heights = [h for _, h in sorter.sort_by_wave_height(DATA)]
        assert heights == sorted(heights, reverse=True)

    def test_empty_and_single(self):
        assert sorter.sort_by_wave_height([]) == []
        assert sorter.sort_by_wave_height([("A", 1.0)]) == [("A", 1.0)]

    def test_none_height_is_treated_as_zero(self):
        """A Location row with no readings yet has wave_height_m = None. The C
        path maps None -> 0.0; the Python fallback must do the same instead of
        raising TypeError on the comparison."""
        result = sorter.sort_by_wave_height([("A", 1.0), ("B", None), ("C", 0.5)])
        assert [n for n, _ in result] == ["A", "C", "B"]

    def test_input_not_mutated(self):
        data = list(DATA)
        sorter.sort_by_wave_height(data)
        assert data == DATA


@pytest.mark.unit
class TestCSortParity:
    @pytest.fixture(autouse=True)
    def require_lib(self):
        if not sorter.HAS_LIBSORT:
            pytest.skip("libmergesort.so not built in this environment")

    def test_c_sort_matches_python_fallback(self, monkeypatch):
        c_result = sorter.sort_by_wave_height(DATA)
        monkeypatch.setattr(sorter, "HAS_LIBSORT", False)
        py_result = sorter.sort_by_wave_height(DATA)
        # Ties (A and D both 1.2) may legitimately come out in either order.
        assert [h for _, h in c_result] == [h for _, h in py_result]
        assert set(c_result) == set(py_result)

    def test_c_sort_handles_none(self):
        result = sorter.sort_by_wave_height([("A", 1.0), ("B", None)])
        assert [n for n, _ in result] == ["A", "B"]
