import unittest
from ema2.slicer import slice_score_path


class TestSelection1(unittest.TestCase):
    def test_selection_1(self):
        new_tree = slice_score_path("../tst/data/ema_test_in.xml", "1,2/all/@1-2")
        new_tree.write("../tst/data/ema_test_out.xml")


if __name__ == '__main__':
    unittest.main()
