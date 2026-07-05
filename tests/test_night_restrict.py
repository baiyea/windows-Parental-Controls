import unittest
from datetime import datetime

import config
from utils.night_restrict import is_in_night_restrict_hours


class NightRestrictTest(unittest.TestCase):
    def setUp(self):
        self.original_config = config.g_config
        config.g_config = {
            "restrict_night_hours": {
                "enabled": True,
                "start_hour": 21,
                "end_hour": 6,
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


if __name__ == "__main__":
    unittest.main()
