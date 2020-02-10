import xml.etree.ElementTree as ET
from ema2.emaexpfull import EmaExpFull


def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ for selecting from a partwise .musicxml file
        uses a deletion based-approach, so ema_exp needs to non-repeating + ascending
    """
    ema_measures = ema_exp_full.selection
    ind = 0
    parts = tree.findall("part")
    for ema_measure in ema_measures:
        # discard measures not == to ema_measure.num
        for part in parts:
            while int(part[ind].attrib['number']) < ema_measure.num:
                part.remove(part[ind])
        ind += 1
    # discard trailing measures
    for part in parts:
        while len(part) > ind:
            part.remove(part[ind])
    return tree