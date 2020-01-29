import unittest
from music21 import corpus


class TestChoralesXML(unittest.TestCase):
    def test_chor_bach_001(self):
        s = corpus.parse('bach/bwv269.xml')
        print(s)
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
