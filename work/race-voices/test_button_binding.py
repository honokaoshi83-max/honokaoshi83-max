import unittest
from button_binding import Capture

class BindingTests(unittest.TestCase):
    def test_existing_hold_and_reconnect_are_ignored(self):
        c=Capture()
        self.assertIsNone(c.update({1:4}))
        self.assertIsNone(c.update({1:4}))
        self.assertIsNone(c.update({1:0}))
        self.assertEqual(c.update({1:4}),(1,3))
        c=Capture();c.update({1:0});c.update({})
        self.assertIsNone(c.update({1:8}))

    def test_other_device_and_multiple_buttons(self):
        c=Capture();c.update({1:0,2:0})
        self.assertEqual(c.update({1:0,2:1<<24}),(2,25))
        c=Capture();c.update({1:0})
        self.assertIsNone(c.update({1:3}))

if __name__=='__main__':unittest.main()
