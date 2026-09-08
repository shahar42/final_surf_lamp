# Running the tests

## One-time setup per clone

```bash
# 1. Install test dependencies into the project venv
esurf/bin/python -m pip install -r requirements-dev.txt

# 2. Turn on the pre-push gate (versioned in .githooks/)
git config core.hooksPath .githooks
```

The `message_wrapper` C++ extension is needed by the V3 protocol tests. If
`import message_wrapper` fails, build it once:

```bash
cd cpp_message_wrapper && ../esurf/bin/python setup.py build_ext --inplace
```

## Day to day

```bash
# everything except firmware (what the pre-push hook runs)
esurf/bin/python -m pytest tests -m "not firmware"

# one group
esurf/bin/python -m pytest tests/unit/web

# one file, verbose
esurf/bin/python -m pytest tests/unit/web/test_threshold_logic.py -v

# skip the slow network-timeout test
esurf/bin/python -m pytest tests -m "not slow"

# firmware logic, compiled natively (needs g++ and make, no Arduino core)
make -C tests/unit/firmware test
# or through pytest:
esurf/bin/python -m pytest tests -m firmware
```

The firmware tests compile the real headers from
`arduino_code/lamp_refractored/lamp_template` against a tiny shim in
`tests/unit/firmware/shim`. `test_protocol` also decodes
`fixtures/v3_sample.bin`, produced by the server's Python encoder, with the
firmware's own header: that is the server-to-lamp contract check. If you
change the encoder, regenerate the fixture:

```bash
esurf/bin/python tests/unit/firmware/gen_v3_fixture.py
```

and commit both fixture files. `tests/unit/protocol/test_v3_fixture_current.py`
fails until you do.

Compiling the actual ESP32 sketch is a separate local step:

```bash
bin/arduino-cli compile --fqbn esp32:esp32:esp32 arduino_code/lamp_refractored/lamp_template
```

`SECRET_KEY` is set automatically by `tests/conftest.py`. No Redis, Postgres,
or network access is needed. The single test that touches the network
(`test_unreachable_redis_fails_fast`) connects to a non-routable address on
purpose and is marked `slow`.

## Adding a test for a new feature

1. Find the row in `TEST_PLAN.md`, or add one. Keep the `Pri` column honest.
2. Put the file in the matching group directory. Unit tests must not touch
   the network, a database, or Redis. Use `fake_redis` from `conftest.py`
   and `freezegun` for time.
3. Name the test after the behaviour, not the function:
   `test_off_hours_wins_over_quiet_hours`, not `test_get_hours_status_2`.
4. If the test guards a fixed bug, say so in the docstring with the commit hash.
5. Run the file, then the whole group, then push. The hook runs everything.

## Layout

```
tests/
  unit/web           helpers, caches, forms, auth helpers      (no I/O)
  unit/protocol      V3 26-byte binary protocol, Python side
  unit/processor     transformer, fallback order, staleness
  unit/firmware      C++ compiled natively with a small Arduino shim
  unit/tools         manufacturing scripts
  integration/web    Flask test client + SQLite + fake Redis
  integration/processor
  fixtures/          sample API payloads
  simulator/         virtual lamp (not built yet)
```

Markers: `unit`, `integration`, `firmware`, `slow`. CI runs
`-m "not firmware"` in the Python job; the firmware job is separate.
