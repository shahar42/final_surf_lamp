"""
The committed firmware parity fixture must match what the encoder produces
today. If this fails, run tests/unit/firmware/gen_v3_fixture.py and commit
both files, then make sure the C++ parity test still passes.
"""

import os

import pytest

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "unit", "firmware", "fixtures")


@pytest.mark.unit
def test_committed_fixture_matches_current_encoder():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gen_v3_fixture", os.path.join(os.path.dirname(FIXTURE_DIR), "gen_v3_fixture.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    with open(os.path.join(FIXTURE_DIR, "v3_sample.bin"), "rb") as f:
        committed = f.read()
    assert committed == gen.encode(), "fixture stale: regenerate with gen_v3_fixture.py"

    with open(os.path.join(FIXTURE_DIR, "v3_sample.txt")) as f:
        assert f.read().strip().splitlines() == gen.expected_lines()
