"""
pytest bridge for the native C++ firmware tests: `pytest -m firmware`.
Runs `make test` in this directory. Skipped when g++ or make is missing,
which is why the pre-push hook deselects the firmware marker and CI runs
it in its own job.
"""

import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.firmware
def test_firmware_suites_pass():
    if not shutil.which("g++") or not shutil.which("make"):
        pytest.skip("g++/make not available")
    result = subprocess.run(["make", "-s", "-C", HERE, "test"], capture_output=True, text=True, timeout=300)
    print(result.stdout)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all suites passed" in result.stdout
