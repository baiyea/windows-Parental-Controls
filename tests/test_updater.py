import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from utils import updater


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size: int = -1):
        return json.dumps(self.payload).encode("utf-8")


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        self.original_config = config.g_config
        config.g_config = {"auto_update": {"enabled": True, "check_interval_minutes": 10}}

    def tearDown(self):
        config.g_config = self.original_config

    def test_check_for_update_uses_asset_matching_latest_version(self):
        release = {
            "tag_name": "v1.7.18",
            "assets": [
                {
                    "name": "ParentControl.windows.1.7.17.exe",
                    "browser_download_url": "https://example.test/old.exe",
                },
                {
                    "name": "ParentControl.windows.1.7.18.exe",
                    "browser_download_url": "https://example.test/new.exe",
                },
            ],
        }

        with (
            patch.object(config, "get_version", return_value="1.7.17"),
            patch.object(updater.urllib.request, "urlopen", return_value=FakeResponse(release)),
        ):
            has_update, download_url, latest_version = updater.check_for_update()

        self.assertTrue(has_update)
        self.assertEqual(download_url, "https://example.test/new.exe")
        self.assertEqual(latest_version, "1.7.18")

    def test_check_for_update_ignores_mismatched_release_asset(self):
        release = {
            "tag_name": "v1.7.18",
            "assets": [
                {
                    "name": "ParentControl.windows.1.7.17.exe",
                    "browser_download_url": "https://example.test/old.exe",
                },
            ],
        }

        with (
            patch.object(config, "get_version", return_value="1.7.17"),
            patch.object(updater.urllib.request, "urlopen", return_value=FakeResponse(release)),
        ):
            has_update, download_url, latest_version = updater.check_for_update()

        self.assertFalse(has_update)
        self.assertIsNone(download_url)
        self.assertIsNone(latest_version)

    def test_apply_pending_update_removes_config_after_copy_succeeds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            current_exe = app_dir / "ParentControl.windows.1.7.17.exe"
            update_dir = app_dir / "update"
            update_dir.mkdir()
            new_exe = update_dir / "ParentControl.windows.1.7.18.exe"
            current_exe.write_bytes(b"old")
            new_exe.write_bytes(b"new")

            with (
                patch.object(updater.sys, "frozen", True, create=True),
                patch.object(updater.sys, "executable", str(current_exe)),
                patch.object(updater.subprocess, "Popen") as popen_mock,
            ):
                self.assertTrue(updater.apply_pending_update())

            script_content = (app_dir / "update.bat").read_text(encoding="utf-8")

        self.assertIn(f'copy /y "{new_exe}" "{current_exe}" || exit /b 1', script_content)
        self.assertIn(f'echo 1.7.18 > "{app_dir / "version.txt"}"', script_content)
        self.assertIn(f'if exist "{app_dir / "config.json"}" del /f /q "{app_dir / "config.json"}"', script_content)
        popen_mock.assert_called_once()

    def test_check_and_download_skips_when_update_is_pending(self):
        with (
            patch.object(updater, "find_pending_update", return_value="pending.exe"),
            patch.object(updater, "check_for_update") as check_mock,
            patch.object(updater, "download_update") as download_mock,
        ):
            result = updater.check_and_download_update()

        self.assertEqual(result, "download_pending")
        check_mock.assert_not_called()
        download_mock.assert_not_called()

    def test_start_periodic_update_check_starts_daemon_thread(self):
        with patch.object(updater.threading, "Thread") as thread_mock:
            thread = updater.start_periodic_update_check()

        self.assertEqual(thread, thread_mock.return_value)
        thread_mock.assert_called_once()
        self.assertTrue(thread_mock.call_args.kwargs["daemon"])
        self.assertEqual(thread_mock.call_args.kwargs["target"], updater.periodic_update_check_loop)
        thread_mock.return_value.start.assert_called_once()

    def test_start_periodic_update_check_skips_when_disabled(self):
        config.g_config["auto_update"]["enabled"] = False

        with patch.object(updater.threading, "Thread") as thread_mock:
            thread = updater.start_periodic_update_check()

        self.assertIsNone(thread)
        thread_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
