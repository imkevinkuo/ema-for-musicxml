import unittest
from ema2.emaexpression import EmaExpression

expr_strs = ["18-18/2+4/@all"]


class ParserTest1(unittest.TestCase):
    def test_0(self):
        ema_expr = EmaExpression(*expr_strs[0].split("/"))
        self.assertEqual(len(ema_expr.mm_ranges), 1)
        self.assertEqual(ema_expr.mm_ranges[0].start, 18)
        self.assertEqual(ema_expr.mm_ranges[0].end, 18)

        self.assertEqual(len(ema_expr.st_ranges), 1)
        self.assertEqual(len(ema_expr.st_ranges[0]), 2)
        self.assertEqual(ema_expr.st_ranges[0][0].start, 2)
        self.assertEqual(ema_expr.st_ranges[0][0].end, 2)
        self.assertEqual(ema_expr.st_ranges[0][1].start, 4)
        self.assertEqual(ema_expr.st_ranges[0][1].end, 4)

        self.assertEqual(len(ema_expr.bt_ranges), 1)
        self.assertEqual(len(ema_expr.bt_ranges[0]), 1)
        self.assertEqual(len(ema_expr.bt_ranges[0][0]), 1)
        self.assertEqual(ema_expr.bt_ranges[0][0][0].start, 'start')
        self.assertEqual(ema_expr.bt_ranges[0][0][0].end, 'end')


if __name__ == '__main__':
    unittest.main()
