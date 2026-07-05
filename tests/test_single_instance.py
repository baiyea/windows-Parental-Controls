import socket
import unittest
from uuid import uuid4

from platform.single_instance import SingleInstance


class SingleInstanceTest(unittest.TestCase):
    def create_instance(self):
        instance = SingleInstance()
        instance.mutex_name = f"Local\\ParentControl.Test.{uuid4()}"
        return instance

    def test_tcp_port_occupation_does_not_block_lock(self):
        blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", 37429))
        blocker.listen(1)
        instance = self.create_instance()

        try:
            self.assertTrue(instance.try_lock())
        finally:
            instance.release()
            blocker.close()

    def test_second_instance_is_blocked(self):
        first = self.create_instance()
        second = SingleInstance()
        second.mutex_name = first.mutex_name

        try:
            self.assertTrue(first.try_lock())
            self.assertFalse(second.try_lock())
        finally:
            second.release()
            first.release()


if __name__ == "__main__":
    unittest.main()
