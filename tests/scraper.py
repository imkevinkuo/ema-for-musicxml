import requests
from music21 import converter, stream, environment
from tqdm import tqdm

from ema2.emaexp import EmaExp
from bs4 import BeautifulSoup
from pyld import jsonld
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from ema2 import emaexp, emaexpfull, slicer
import os.path

W3C_HAS_SRC = "http://www.w3.org/ns/oa#hasSource"
NANOPUB_URL = "http://digitalduchemin.org:8080/nanopub-server"
LAST_PAGE = 11


def get_jsonlds(page_num):
    """ Fetches a list of .jsonld file URLs for each nanopub on the specified page. """
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


def ema_exp_from_jsonld(jsonld_filename):
    """ Gets the EMA URL from a jsonld, then constructs an EmaExp from the URL. """
    ema_url = ema_url_from_jsonld(jsonld_filename)
    return EmaExp(*ema_url.split("/")[:-3])


def ema_exps_from_page(page_num):
    """ Constructs an EmaExp for every nanopub on the page. """
    file_names = get_jsonlds(page_num)
    ema_exps = []
    for file_name in file_names:
        ema_exps.append(ema_exp_from_jsonld(file_name))
    return ema_exps


def add_omas_sel_truth_to_dict(d, page_num):
    """ Add entries to a dictionary[score_name][ema_string] = selection xml for each nanopub on the specified page. """
    jsonlds = get_jsonlds(page_num)
    ema_urls = [ema_url_from_jsonld(j) for j in jsonlds]
    mei_urls = [unquote(ema_url.split("/")[-4]) for ema_url in ema_urls]
    fails = []

    for i in tqdm(range(len(mei_urls))):
        mei_url = mei_urls[i]
        ema_url = ema_urls[i]

        filename = mei_url.split("/")[-1]
        name_ext = filename.split(".")
        expr = ema_url.split("/")[-3:]

        # Can't suppress "mei.base: WARNING: Importing <slur> without @startid and @endid is not yet supported."
        try:
            # Downloads the MEI score, converts to XML, saves as a file. Use etree to load from file.
            if not os.path.exists(f"data/{filename}"):
                score = converter.parseURL(mei_url, format='mei')
                score.write("musicxml", fp=f"data/{filename}")

            # Saves the MEI selection into a temp file and loads it back into memory.
            selection_score = converter.parseURL(ema_url, format='mei')
            selection_path = selection_score.write("musicxml", fp=f"data/temp_selection.xml")
            omas_tree = ET.parse(selection_path)

            if name_ext[0] not in d:
                d[name_ext[0]] = {}
            d[name_ext[0]]["/".join(expr)] = omas_tree # Maybe ET.tostring
        # except converter.ConverterException:
        except Exception as ex:
            fails.append((i,ex))
            # print(f"{i}: {ex]")

    return d, fails


def ema2_vs_omas(selections_truth, score_name, expr_str):
    """
    TODO: Compare the XML.
    """

    # data/score_name.xml should have been downloaded when running get_omas_selections.
    tree = ET.parse(f"data/{score_name}.xml")
    ema_exp = emaexp.EmaExp(*expr_str.split("/"))
    score_info = emaexpfull.get_score_info_mxl(tree)
    ema_exp_full = emaexpfull.EmaExpFull(score_info, ema_exp)
    ema2_tree = slicer.slice_score(tree, ema_exp_full)
    # Make a diff report - compare to selections_truth[score_name][expr]


def scrape_all_scores():
    d = {}
    fails = []
    for i in range(1, LAST_PAGE + 1):
        d2, fails2 = add_omas_sel_truth_to_dict(d, i)
        fails += fails2
    return d, fails


def get_omas_and_ema2_trees(npub_num):
    """ delete this soon
    """
    page_num = 1 + (npub_num // 1000)
    npub_num = npub_num % 1000

    jsonlds = get_jsonlds(page_num)
    ema_urls = [ema_url_from_jsonld(j) for j in jsonlds]
    mei_urls = [unquote(ema_url.split("/")[-4]) for ema_url in ema_urls]
    #
    ema_url = ema_urls[npub_num]
    mei_url = mei_urls[npub_num]
    filename = mei_url.split("/")[-1]
    name_ext = filename.split(".")
    expr = ema_url.split("/")[-3:]
    #  get the selection
    selection_score: stream.Score = converter.parseURL(ema_url, format='mei')
    selection_path = selection_score.write("musicxml", fp=f"data/{name_ext[0]}_selection.{name_ext[1]}")
    omas_tree = ET.parse(selection_path)
    #  get the original, slice it
    score = converter.parseURL(mei_url, format='mei')
    path = score.write("musicxml", fp=f"data/{filename}")
    tree = ET.parse(path)
    ema_exp = emaexp.EmaExp(*expr)
    score_info = emaexpfull.get_score_info_mxl(tree)
    ema_exp_full = emaexpfull.EmaExpFull(score_info, ema_exp)
    ema2_tree = slicer.slice_score(tree, ema_exp_full)
    ##
    return omas_tree, ema2_tree


def export_trees(o, e):
    o.write('o.xml')
    e.write('e.xml')

environment.set('autoDownload', 'allow')
