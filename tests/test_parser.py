import unittest
import tests.scraper as scraper
from ema2.emaexp import EmaExp

expr_strs = ["18-18/2+4/@all"]


class ParserTest0(unittest.TestCase):
    def test_0(self):
        ema_expr = EmaExp.fromstring(expr_strs[0])
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

    def test_parse_all_pages(self):
        for i in range(1, scraper.LAST_PAGE + 1):
            for ema_exp in scraper.ema_exps_from_page(i):
                self.assertIsNotNone(ema_exp)

    def test_simplify_expr(self):
        """
        Rules for parser expressions:

        2,1/all/@all - allow: return in order
        2,2/all@all - allow: simplify so no duplicates
        how do i handle repeats?

        expr that maps to entire xml:
        start-10,11-end/all/@all
        all/all/@all
        start-10,11-end/all,all/@all
        0-21/all/@all

        """
        self.assertTrue(False)


if __name__ == '__main__':
    unittest.main()
