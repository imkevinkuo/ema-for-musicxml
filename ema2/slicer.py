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
            # requested measure
            else:
                ema_measure = ema_measures[m]
                # if stave in selection, choose beats
                if s+1 in ema_measure.staves:
                    beats = ema_measure.staves[s + 1]
                    # need division length by looking at signature changes
                    divisions = 10080
                    time = 0
                    notes = measure.findall("note")
                    for n in range(len(notes)):
                        note = notes[n]
                        duration = int(note.find("duration").text)
                        if (time / divisions) + 1 not in beats:
                            rest = None  # how do i make a rest
                            measure.insert(n, rest)
                            measure.remove(note)
                        time += duration
                # else, blank measure
                else:
                    for note in measure.findall("note"):
                        measure.remove(note)
                # increment m after processing a requested measure
                m += 1
    return tree
