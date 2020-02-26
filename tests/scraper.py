import requests
from music21 import converter, stream
from ema2.emaexp import EmaExp
from bs4 import BeautifulSoup
from pyld import jsonld
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from ema2 import emaexp, emaexpfull, slicer

W3C_HAS_SRC = "http://www.w3.org/ns/oa#hasSource"
NANOPUB_URL = "http://digitalduchemin.org:8080/nanopub-server"
LAST_PAGE = 11


def get_jsonlds(page_num):
    r = requests.get(f"{NANOPUB_URL}/nanopubs.html?page={page_num}")
    soup = BeautifulSoup(r.text, 'html.parser')
    results = soup.findAll("a", text="jsonld", attrs={"type": "application/ld+json"})
    file_names = [x.attrs["href"] for x in results]
    return file_names


def ema_url_from_jsonld(jsonld_filename):
    nanopub = jsonld.load_document(f"{NANOPUB_URL}/{jsonld_filename}")
    for graph in nanopub["document"]:
        for item in graph["@graph"]:
            if W3C_HAS_SRC in item:
                return item[W3C_HAS_SRC][0]['@id']
    return None


def ema_exp_from_jsonld(jsonld_filename):
    ema_url = ema_url_from_jsonld(jsonld_filename)
    return EmaExp(*ema_url.split("/")[:-3])


def ema_exps_from_page(page_num):
    file_names = get_jsonlds(page_num)
    ema_exps = []
    for file_name in file_names:
        ema_exps.append(ema_exp_from_jsonld(file_name))
    return ema_exps


# We need to construct a dictionary[score_name][ema_string] = selection xml.
# Script to download all files and convert to xml.
def get_omas_and_ema2_trees(npub_num):
    """ Takes a single nanopub and executes the following steps:
    1. Converts the MEI score to MusicXML.
    2. Converts the MEI selection to MusicXML.
    3. Runs the slicer on the MEI-to-MXL score.
    TODO: Compare the XML outputs of 2 and 3.
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
