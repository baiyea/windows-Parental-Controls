import unittest

from ui.lock_screen import LockScreen


class FakeRoot:
    def __init__(self):
        self.attribute_calls = []
        self.after_calls = []
        self.after_cancel_calls = []
        self.deiconify_calls = 0
        self.lift_calls = 0

    def attributes(self, *args):
        self.attribute_calls.append(args)

    def deiconify(self):
        self.deiconify_calls += 1

    def lift(self):
        self.lift_calls += 1

    def after(self, delay_ms, callback):
        self.after_calls.append((delay_ms, callback))
        return f"after-{len(self.after_calls)}"

    def after_cancel(self, after_id):
        self.after_cancel_calls.append(after_id)


class FakeEntry:
    def __init__(self):
        self.focus_set_calls = 0

    def focus_set(self):
        self.focus_set_calls += 1


class LockScreenFocusGuardTest(unittest.TestCase):
    def test_enforce_lock_focus_keeps_single_topmost_guard(self):
        lock_screen = LockScreen.__new__(LockScreen)
        lock_screen.root = FakeRoot()
        lock_screen.pwd_entry = FakeEntry()
        lock_screen.closed = False
        lock_screen._focus_guard_after_id = None

        lock_screen.enforce_lock_focus()
        lock_screen.enforce_lock_focus()

        self.assertIn(("-fullscreen", True), lock_screen.root.attribute_calls)
        self.assertIn(("-topmost", True), lock_screen.root.attribute_calls)
        self.assertEqual(lock_screen.root.deiconify_calls, 2)
        self.assertEqual(lock_screen.root.lift_calls, 2)
        self.assertEqual(lock_screen.pwd_entry.focus_set_calls, 2)
        self.assertEqual(len(lock_screen.root.after_calls), 2)
        self.assertEqual(lock_screen.root.after_cancel_calls, ["after-1"])
        self.assertEqual(lock_screen.root.after_calls[1][0], LockScreen.FOCUS_GUARD_INTERVAL_MS)

    def test_focus_out_requests_short_delayed_restore(self):
        lock_screen = LockScreen.__new__(LockScreen)
        lock_screen.root = FakeRoot()
        lock_screen.pwd_entry = FakeEntry()
        lock_screen.closed = False
        lock_screen._focus_guard_after_id = None

        lock_screen.request_focus_guard()

        self.assertEqual(lock_screen.root.after_calls[0][0], LockScreen.FOCUS_RESTORE_DELAY_MS)

    def test_focus_guard_stops_when_closed(self):
        lock_screen = LockScreen.__new__(LockScreen)
        lock_screen.root = FakeRoot()
        lock_screen.pwd_entry = FakeEntry()
        lock_screen.closed = True
        lock_screen._focus_guard_after_id = None

        lock_screen.enforce_lock_focus()

        self.assertEqual(lock_screen.root.attribute_calls, [])
        self.assertEqual(lock_screen.root.after_calls, [])


if __name__ == "__main__":
    unittest.main()
