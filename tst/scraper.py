import os.path
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from pyld import jsonld
from urllib.parse import unquote

from io import StringIO
import sys

import xml.etree.ElementTree as ET
from music21 import converter, environment

W3C_HAS_SRC = "http://www.w3.org/ns/oa#hasSource"
NANOPUB_URL = "http://digitalduchemin.org:8080/nanopub-server"
LAST_PAGE = 11

# To access ema2 module from inside tst folder
sys.path.append(os.path.abspath(os.path.join('..', 'ema2')))
from ema2.emaexp import EmaExp
from ema2 import emaexp, emaexpfull, slicer


# For suppressing music21 warnings, so the tqdm progress bar is not reprinted upon warnings
class Capturing(list):
    def __enter__(self):
        self._stderr = sys.stderr
        sys.stderr = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stderr = self._stderr


#
# Scraping functions
#
def scrape_page_nanopubs(page_num, d={}, fails={}):
    """
    Scrapes all nanopubs from the page.
    Saves score xml + selection xml to disk.
    Returns dict[nanopub_num] = (score_name, ema_expression) for reference.
    """
    jsonlds = get_jsonlds(page_num)
    for i in tqdm(range(len(jsonlds))):
        nanopub_num = 1000*(page_num - 1) + i
        try:
            with Capturing() as output:
                score_name, expr_str = scrape_nanopub(nanopub_num, jsonlds[i])
                d[nanopub_num] = (score_name, expr_str)
        except Exception as ex:
            fails[nanopub_num] = ex

    return d, fails


def scrape_nanopub(nanopub_num, jsonld_filename):
    ema_url = ema_url_from_jsonld(jsonld_filename)
    mei_url = unquote(ema_url.split("/")[-4])
    expr_str = "/".join(ema_url.split("/")[-3:])
    score_name = mei_url.split("/")[-1].split(".")[0]
    #
    # Will warn "mei.base: WARNING: Importing <slur> without @startid and @endid is not yet supported."
    #
    # Downloads the MEI score, converts to XML, saves as a file. Use etree to load from file.
    score_path = f"data/scores/{score_name}.xml"
    if not os.path.exists(score_path):
        score = converter.parseURL(mei_url, format='mei')
        score.write("musicxml", fp=score_path)

    # Downloads the MEI selection, converts to XML, saves as a file, and stores etree in the dict.
    selection_path = f"data/selections/nanopub_{nanopub_num}.xml"
    if not os.path.exists(selection_path):
        selection_score = converter.parseURL(ema_url, format='mei')
        selection_score.write("musicxml", fp=selection_path)

    return score_name, expr_str


#
# Evaluation functions
#
def evaluate_ema2_page(page_num):
    jsonlds = get_jsonlds(page_num)
    for i in range(len(jsonlds)):
        nanopub_num = 1000 * (page_num - 1) + i
        ema_url = ema_url_from_jsonld(jsonlds[i])
        mei_url = unquote(ema_url.split("/")[-4])
        expr_str = "/".join(ema_url.split("/")[-3:])
        score_name = mei_url.split("/")[-1].split(".")[0]

        try:
            evaluate_ema2(score_name, expr_str, f"nanopub_{nanopub_num}")
        except Exception as ex:
            print(f"Exception for nanopub_{nanopub_num}: {ex}")


def evaluate_ema2(score_name, expr_str, truth_filename, print_fail_elem=False):
    # TODO: Maybe try downloading if we can't find it
    score_path = f"data/scores/{score_name}.xml"
    selection_path = f"data/selections/{truth_filename}.xml"
    if not os.path.exists(score_path):
        print(f"Skipping {truth_filename}; score not found.")
        return
    if not os.path.exists(selection_path):
        print(f"Skipping {truth_filename}; selection not found.")
        return

    print(f"Evaluating {truth_filename}")
    ema2_tree = slicer.slice_score_path(score_path, expr_str)
    omas_tree = ET.parse(selection_path)
    diff_test(ema2_tree.getroot(), omas_tree.getroot(), print_fail_elem)
    # For debugging
    ema2_tree.write("data/selection_temp.xml")
    return ema2_tree, omas_tree


# Suggested usage: Open Python console, run this function,
# then compare the content of selection_temp.xml and selections/nanopub_X.xml.
def evaluate_ema2_by_num(nanopub_num, print_fail_elem=False):
    """ Evaluates a single nanopub. """
    page_num = 1 + nanopub_num // 1000
    jsonlds = get_jsonlds(page_num)
    score_name, expr_str = scrape_nanopub(nanopub_num, jsonlds[nanopub_num % 1000])
    return evaluate_ema2(score_name, expr_str, f"nanopub_{nanopub_num}", print_fail_elem)
# List of failing nanopubs (but are okay to ignore)
# Selection on digital du chemin is incorrect (usually minor errors):
# 22, 31, 35, 63, 67, 70, 74, 106
# bad music21 conversion / malformed score:
# 40, 85


def diff_test(elem1: ET.Element, elem2: ET.Element, print_fail_elem):
    """ A simple recursive function that checks if the structure and tags of these two trees are generally the same. """
    if len(elem1) == len(elem2) and elem1.tag == elem2.tag:
        # print(f"Matched {root1.tag}: {len(root1)} children.")
        # TODO: Is it wise to sort? The nanopubs might have elements out of order
        #  (or maybe music21 conversion jumbled them up)
        # Leaving staves unsorted (by id) seems okay
        elem1 = sorted(list(elem1), key=lambda x: (x.tag, x.get('id', None) if x.tag != 'part' else None))
        elem2 = sorted(list(elem2), key=lambda x: (x.tag, x.get('id', None) if x.tag != 'part' else None))
        for i in range(len(elem1)):
            diff_test(elem1[i], elem2[i], print_fail_elem)
    else:
        print(f"Mismatch at {elem1.tag}, {elem1.attrib}: {len(elem1)} children vs. {elem2.tag}, {elem2.attrib}: {len(elem2)} children.")
        if print_fail_elem:
            print_elems_recursive(elem1)
            print_elems_recursive(elem2)


#
# Utility functions for tst and scraper
#
def get_jsonlds(page_num):
    """ Fetches a list of .jsonld file URLs on the specified page. """
    r = requests.get(f"{NANOPUB_URL}/nanopubs.html?page={page_num}")
    soup = BeautifulSoup(r.text, 'html.parser')
    results = soup.findAll("a", text="jsonld", attrs={"type": "application/ld+json"})
    file_names = [x.attrs["href"] for x in results]
    return file_names


def ema_url_from_jsonld(jsonld_filename):
    """ Takes a .jsonld filename and extracts the full EMA request URL. """
    nanopub = jsonld.load_document(f"{NANOPUB_URL}/{jsonld_filename}")
    for graph in nanopub["document"]:
        for item in graph["@graph"]:
            if W3C_HAS_SRC in item:
                return item[W3C_HAS_SRC][0]['@id']
    return None


def ema_exps_from_page(page_num):
    """ Constructs an EmaExp for every nanopub on the page. """
    file_names = get_jsonlds(page_num)
    ema_exps = []
    for file_name in file_names:
        ema_url = ema_url_from_jsonld(file_name)
        ema_exps.append(EmaExp(*ema_url.split("/")[:-3]))
    return ema_exps


def print_elems_recursive(elem, i=0):
    print(" "*i, elem)
    for child in elem:
        print_elems_recursive(child, i+4)


environment.set('autoDownload', 'allow')

if __name__ == '__main__' and len(sys.argv) == 2 and sys.argv[1] == "scrape":
    print(os.getcwd())
    if os.path.basename(os.getcwd()) == 'ema2':
        os.chdir('tst')

    if os.path.basename(os.getcwd()) != 'tst':
        print("\"scraper.py scrape\" should be run from within the ema2 root folder or ema2/tst.")
        exit()

    if not os.path.exists("data"):
        os.mkdir('data')
        os.mkdir('data/selections')
        os.mkdir('data/scores')
    for p in range(1, LAST_PAGE+1):
        scrape_page_nanopubs(p)
