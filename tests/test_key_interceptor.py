import ctypes
import unittest
from unittest.mock import patch

from utils import key_interceptor
from utils.key_interceptor import KBDLLHOOKSTRUCT, KeyInterceptor


class FakeLogger:
    def debug(self, _message):
        return None

    def error(self, _message):
        return None


class KeyInterceptorTest(unittest.TestCase):
    def setUp(self):
        self.keyboard_structs = []

    def _lparam_for_key(self, vk_code):
        keyboard_struct = KBDLLHOOKSTRUCT(
            vkCode=vk_code,
            scanCode=0,
            flags=0,
            time=0,
            dwExtraInfo=None,
        )
        self.keyboard_structs.append(keyboard_struct)
        return ctypes.cast(ctypes.pointer(keyboard_struct), ctypes.c_void_p).value

    def test_blocks_windows_key_release_messages(self):
        interceptor = KeyInterceptor()

        with patch.object(key_interceptor, "_get_logger", return_value=FakeLogger()):
            self.assertEqual(
                interceptor._keyboard_hook_callback(
                    0,
                    KeyInterceptor.WM_KEYUP,
                    self._lparam_for_key(KeyInterceptor.VK_LWIN),
                ),
                1,
            )
            self.assertEqual(
                interceptor._keyboard_hook_callback(
                    0,
                    KeyInterceptor.WM_SYSKEYUP,
                    self._lparam_for_key(KeyInterceptor.VK_RWIN),
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
