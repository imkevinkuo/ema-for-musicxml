import unittest
import requests
from bs4 import BeautifulSoup
from pyld import jsonld
from ema2.emaexp import EmaExp

expr_strs = ["18-18/2+4/@all"]
W3C_HAS_SRC = "http://www.w3.org/ns/oa#hasSource"
NANOPUB_URL = "http://digitalduchemin.org:8080/nanopub-server"
LAST_PAGE = 11


class ParserTest0(unittest.TestCase):
    def test_0(self):
        ema_expr = EmaExp(*expr_strs[0].split("/"))
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

    def test_parse_no_error_single_page(self):
        i = 1
        file_names = get_nanopub_jsonlds(i)
        for file_name in file_names:
            ema_expr_list = get_ema_expr_from_jsonld_filename(file_name)
            ema_expr = EmaExp(*ema_expr_list)
            self.assertIsNotNone(ema_expr)

    def test_parse_no_error(self):
        for i in range(1, LAST_PAGE + 1):
            file_names = get_nanopub_jsonlds(i)
            for file_name in file_names:
                ema_expr_list = get_ema_expr_from_jsonld_filename(file_name)
                self.assertIsNotNone(ema_expr_list)
                ema_expr = EmaExp(*ema_expr_list)
                self.assertIsNotNone(ema_expr)

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


def get_nanopub_jsonlds(page_num):
    r = requests.get(f"{NANOPUB_URL}/nanopubs.html?page={page_num}")
    soup = BeautifulSoup(r.text, 'html.parser')
    results = soup.findAll("a", text="jsonld", attrs={"type": "application/ld+json"})
    file_names = [x.attrs["href"] for x in results]
    return file_names


def get_ema_expr_from_jsonld_filename(jsonld_filename):
    nanopub = jsonld.load_document(f"{NANOPUB_URL}/{jsonld_filename}")
    for graph in nanopub["document"]:
        for item in graph["@graph"]:
            if W3C_HAS_SRC in item:
                ema_url = item[W3C_HAS_SRC][0]['@id']
                return ema_url.split("/")[-3:]
    return None


if __name__ == '__main__':
    unittest.main()
