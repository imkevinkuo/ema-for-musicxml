import os.path
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from pyld import jsonld
from urllib.parse import unquote

import xml.etree.ElementTree as ET
from ema2.emaexp import EmaExp
from ema2 import emaexp, emaexpfull, slicer
from music21 import converter, stream, environment

W3C_HAS_SRC = "http://www.w3.org/ns/oa#hasSource"
NANOPUB_URL = "http://digitalduchemin.org:8080/nanopub-server"
LAST_PAGE = 11


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
    # May warn "mei.base: WARNING: Importing <slur> without @startid and @endid is not yet supported."
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
    score_tree = ET.parse(score_path)
    ema_exp = emaexp.EmaExp(*expr_str.split("/"))
    score_info = emaexpfull.get_score_info_mxl(score_tree)
    ema_exp_full = emaexpfull.EmaExpFull(score_info, ema_exp)

    ema2_tree = slicer.slice_score(score_tree, ema_exp_full)
    omas_tree = ET.parse(selection_path)
    diff_test(ema2_tree.getroot(), omas_tree.getroot(), print_fail_elem)
    # For debugging
    ema2_tree.write("data/selection_temp.xml")
    return ema2_tree, omas_tree


def evaluate_ema2_by_num(nanopub_num, print_fail_elem=False):
    """ Use this for testing! """
    page_num = 1 + nanopub_num // 1000
    jsonlds = get_jsonlds(page_num)
    score_name, expr_str = scrape_nanopub(nanopub_num, jsonlds[nanopub_num % 1000])
    return evaluate_ema2(score_name, expr_str, f"nanopub_{nanopub_num}", print_fail_elem)


def diff_test(root1, root2, print_fail_elem):
    """ A simple recursive function that checks if the structure and tags of these two trees are generally the same. """
    if len(root1) == len(root2) and root1.tag == root2.tag:
        # print(f"Matched {root1.tag}: {len(root1)} children.")
        for i in range(len(root1)):
            diff_test(root1[i], root2[i], print_fail_elem)
    else:
        print(f"Match failed: {root1.tag}: {len(root1)} children vs. {root2.tag}: {len(root2)} children.")
        if print_fail_elem:
            print_elems_recursive(root1)
            print_elems_recursive(root2)


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

# List of failing nanopubs (because of external reasons)
#num |
# 22 | Exp should be 5-6/1+2/@all
# 31 | Exp should be 13-13/2+3/@all
# 35 | Omas selection is wrong
# 40 | bad music21 conversion
