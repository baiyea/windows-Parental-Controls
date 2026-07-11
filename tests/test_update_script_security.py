import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class FakeLocker:
    def try_lock(self):
        return True


class FakeApp:
    def start(self):
        return None


class UpdateScriptSecurityTest(unittest.TestCase):
    def test_main_ignores_stray_update_script_on_startup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            exe_path = app_dir / "ParentControl.exe"
            (app_dir / "update.bat").write_text("echo unsafe", encoding="utf-8")

            with (
                patch.object(main.sys, "frozen", True, create=True),
                patch.object(main.sys, "executable", str(exe_path)),
                patch.object(main.sys, "argv", [str(exe_path)]),
                patch.object(main, "load_config"),
                patch.object(main, "run_auto_update", return_value=None),
                patch.object(main, "start_periodic_update_check") as update_check_mock,
                patch.object(main, "SingleInstance", return_value=FakeLocker()),
                patch.object(main, "ParentControl", return_value=FakeApp()),
                patch.object(os, "system") as system_mock,
            ):
                main.main()

        system_mock.assert_not_called()
        update_check_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
