import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import config
from utils.night_restrict import (
    activate_night_unlock_override,
    is_in_night_restrict_hours,
    is_night_restrict_enforced,
    is_night_unlock_override_active,
)


class NightRestrictTest(unittest.TestCase):
    def setUp(self):
        self.original_config = config.g_config
        config.g_config = {
            "restrict_night_hours": {
                "enabled": True,
                "start_hour": 21,
                "end_hour": 6,
                "password_unlock_grace_minutes": 30,
                "override_until": None,
            }
        }

    def tearDown(self):
        config.g_config = self.original_config

    def test_cross_day_window_contains_late_evening(self):
        self.assertTrue(is_in_night_restrict_hours(now=datetime(2026, 7, 5, 22, 0)))

    def test_cross_day_window_contains_early_morning(self):
        self.assertTrue(is_in_night_restrict_hours(now=datetime(2026, 7, 6, 5, 59)))

    def test_cross_day_window_excludes_daytime(self):
        self.assertFalse(is_in_night_restrict_hours(now=datetime(2026, 7, 5, 14, 0)))

    def test_disabled_config_returns_false(self):
        config.g_config["restrict_night_hours"]["enabled"] = False

        self.assertFalse(is_in_night_restrict_hours(now=datetime(2026, 7, 5, 22, 0)))

    def test_override_active_suppresses_night_enforcement(self):
        now = datetime(2026, 7, 5, 22, 0)
        config.g_config["restrict_night_hours"]["override_until"] = "2026-07-05 22:30:00"

        self.assertTrue(is_in_night_restrict_hours(now=now))
        self.assertTrue(is_night_unlock_override_active(now=now))
        self.assertFalse(is_night_restrict_enforced(now=now))

    def test_override_expired_allows_night_enforcement(self):
        now = datetime(2026, 7, 5, 22, 31)
        config.g_config["restrict_night_hours"]["override_until"] = "2026-07-05 22:30:00"

        self.assertFalse(is_night_unlock_override_active(now=now))
        self.assertTrue(is_night_restrict_enforced(now=now))

    def test_activate_override_uses_configured_grace_minutes(self):
        now = datetime(2026, 7, 5, 22, 0)

        with patch.object(config, "save_config"):
            override_until = activate_night_unlock_override(now=now)

        self.assertEqual(override_until, now + timedelta(minutes=30))
        self.assertEqual(
            config.g_config["restrict_night_hours"]["override_until"],
            "2026-07-05 22:30:00",
        )


if __name__ == "__main__":
    unittest.main()
