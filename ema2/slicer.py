import xml.etree.ElementTree as ET
from ema2.emaexpressionfull import EmaExpressionFull


# partwise - also only works on .musicxml, not .mxl (compressed format)
# restrict inputs to ascending order, non repeating, use deletion-based approach
def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpressionFull):
    return tree


def append_beats(new_measure, beats, old_measure):
    for x in old_measure:
        # if x.tag == 'note' or x.tag == 'rest':
        new_measure.append(x)
    return new_measure
