import xml.etree.ElementTree as ET
from ema2.emaexpfull import EmaExpFull


def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ for selecting from a partwise .musicxml file
        uses a deletion based-approach, so ema_exp needs to non-repeating + ascending
    """
    ema_measures = ema_exp_full.selection
    m = 0
    staves = tree.findall("part")
    for s in range(len(staves)):  # staff
        m = 0
        while m < len(staves[s]):
            measure = staves[s][m]
            # I want to use m < ema_measures[m].num but this may not take repeats or pickup measure into account
            # also problems with non-integer measures
            # removes trailing measures | removes non-requested measures
            if m >= len(ema_measures) or int(measure.attrib['number']) != ema_measures[m].num:
                staves[s].remove(measure)
                print(f"removed measure {measure.attrib['number']} from part {s}")
            # requested measure
            else:
                ema_measure = ema_measures[m]
                # if stave in selection, choose beats
                if s+1 in ema_measure.staves:
                    beats = ema_measure.staves[s+1]
                # else, blank measure
                else:
                    for note in measure.findall("note"):
                        measure.remove(note)
                # increment m after processing a requested measure
                m += 1
    return tree
