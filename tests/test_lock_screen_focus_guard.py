import unittest

from ui.lock_screen import LockScreen


class FakeRoot:
    def __init__(self):
        self.attribute_calls = []
        self.after_calls = []
        self.lift_calls = 0
        self.focus_force_calls = 0

    def attributes(self, *args):
        self.attribute_calls.append(args)

    def lift(self):
        self.lift_calls += 1

    def focus_force(self):
        self.focus_force_calls += 1

    def after(self, delay_ms, callback):
        self.after_calls.append((delay_ms, callback))


class FakeEntry:
    def __init__(self):
        self.focus_force_calls = 0

    def focus_force(self):
        self.focus_force_calls += 1


class LockScreenFocusGuardTest(unittest.TestCase):
    def test_enforce_lock_focus_keeps_single_topmost_guard(self):
        lock_screen = LockScreen.__new__(LockScreen)
        lock_screen.root = FakeRoot()
        lock_screen.pwd_entry = FakeEntry()
        lock_screen.closed = False
        lock_screen._focus_guard_scheduled = False

        lock_screen.enforce_lock_focus()
        lock_screen.enforce_lock_focus()

        self.assertIn(("-fullscreen", True), lock_screen.root.attribute_calls)
        self.assertIn(("-topmost", True), lock_screen.root.attribute_calls)
        self.assertEqual(lock_screen.root.lift_calls, 2)
        self.assertEqual(lock_screen.root.focus_force_calls, 2)
        self.assertEqual(lock_screen.pwd_entry.focus_force_calls, 2)
        self.assertEqual(len(lock_screen.root.after_calls), 1)
        self.assertEqual(lock_screen.root.after_calls[0][0], LockScreen.FOCUS_GUARD_INTERVAL_MS)

    def test_focus_guard_stops_when_closed(self):
        lock_screen = LockScreen.__new__(LockScreen)
        lock_screen.root = FakeRoot()
        lock_screen.pwd_entry = FakeEntry()
        lock_screen.closed = True
        lock_screen._focus_guard_scheduled = False

        lock_screen.enforce_lock_focus()

        self.assertEqual(lock_screen.root.attribute_calls, [])
        self.assertEqual(lock_screen.root.after_calls, [])


if __name__ == "__main__":
    unittest.main()
