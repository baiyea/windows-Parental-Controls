# Trusted Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make parental-control timing decisions use trusted online NTP time, and lock the app when trusted time is unavailable.

**Architecture:** Add a focused trusted-time utility that syncs from Aliyun/Tencent NTP and projects current time using `time.monotonic()`. Existing control modules consume `trusted_now()` instead of local system time for enforcement decisions.

**Tech Stack:** Python 3.13, standard-library `socket`, `struct`, `time`, `datetime`, `unittest`.

---

## File Structure

- Create `utils/trusted_time.py`: trusted clock implementation, NTP client, exceptions, module-level helpers.
- Modify `utils/night_restrict.py`: accept an optional `now` value and default to trusted time.
- Modify `core/controller.py`: replace control-related `datetime.now()` calls with trusted time helpers and fail-closed behavior.
- Modify `config.py` and `config.json`: add default trusted-time configuration.
- Create `tests/test_trusted_time.py`: trusted-time unit tests.
- Create `tests/test_night_restrict.py`: night restriction time-source tests.
- Create `tests/test_controller_trusted_time.py`: controller fail-closed startup test.

## Task 1: Trusted Time Utility

**Files:**
- Create: `utils/trusted_time.py`
- Test: `tests/test_trusted_time.py`

- [ ] **Step 1: Write failing tests**

Create tests for successful sync, monotonic projection, and all-server failure.

- [ ] **Step 2: Verify tests fail**

Run: `uv run python -m unittest tests.test_trusted_time -v`

Expected: import failure for `utils.trusted_time`.

- [ ] **Step 3: Implement utility**

Implement `TrustedClock`, `NtpClient`, `TrustedTimeUnavailable`, `trusted_now()`, `sync_now()`, and `is_available()`.

- [ ] **Step 4: Verify tests pass**

Run: `uv run python -m unittest tests.test_trusted_time -v`

Expected: all tests pass.

## Task 2: Night Restriction Uses Trusted Time

**Files:**
- Modify: `utils/night_restrict.py`
- Test: `tests/test_night_restrict.py`

- [ ] **Step 1: Write failing tests**

Test that `is_in_night_restrict_hours(now=fixed_time)` uses the supplied time and handles cross-day windows.

- [ ] **Step 2: Verify tests fail**

Run: `uv run python -m unittest tests.test_night_restrict -v`

Expected: `TypeError` because `now` is not accepted yet.

- [ ] **Step 3: Implement minimal change**

Allow optional `now`; when omitted, call `trusted_now()`.

- [ ] **Step 4: Verify tests pass**

Run: `uv run python -m unittest tests.test_night_restrict -v`

Expected: all tests pass.

## Task 3: Controller Fails Closed

**Files:**
- Modify: `core/controller.py`
- Test: `tests/test_controller_trusted_time.py`

- [ ] **Step 1: Write failing test**

Test that startup triggers lock restore when trusted time sync fails.

- [ ] **Step 2: Verify test fails**

Run: `uv run python -m unittest tests.test_controller_trusted_time -v`

Expected: controller starts normal flow instead of lock restore, or trusted-time hook is missing.

- [ ] **Step 3: Implement fail-closed startup and trusted-time reads**

Add a `_now()` helper, call `sync_now()` at startup, replace enforcement `datetime.now()` calls with `_now()`, and lock on `TrustedTimeUnavailable`.

- [ ] **Step 4: Verify test passes**

Run: `uv run python -m unittest tests.test_controller_trusted_time -v`

Expected: all tests pass.

## Task 4: Config Defaults and Full Verification

**Files:**
- Modify: `config.py`
- Modify: `config.json`
- Run all tests

- [ ] **Step 1: Add config defaults**

Add `trusted_time` default values and migration when missing from loaded config.

- [ ] **Step 2: Run unit tests**

Run: `uv run python -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 3: Static check**

Run: `uv run ruff check .`

Expected: no new lint errors from touched files.

## Self Review

- Spec coverage: NTP servers, trusted monotonic projection, fail-closed lock behavior, config defaults, and tests are covered.
- Placeholder scan: no TBD or undefined implementation steps remain.
- Type consistency: plan uses `TrustedTimeUnavailable`, `TrustedClock`, `trusted_now()`, `sync_now()`, and `is_available()` consistently.
