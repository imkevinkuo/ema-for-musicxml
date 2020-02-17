import xml.etree.ElementTree as ET
from ema2.emaexpfull import EmaExpFull


def convert_to_rest(note):
    # remove everything that isn't duration, type, voice, or lyrics
    note_remove = ["pitch", "stem"]
    for r in note_remove:
        note_elem = note.find(r)
        if note_elem:
            note.remove(note_elem)
    note.insert(ET.Element("rest"))


def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ for selecting from a partwise .musicxml file
        uses a deletion based-approach, so ema_exp needs to non-repeating + ascending
    """
    ema_measures = ema_exp_full.selection
    staves = tree.findall("part")
    for s in range(len(staves)):  # staff
        m = 0
        divisions = 0
        while m < len(staves[s]):
            measure = staves[s][m]

            # detect time signature change
            m_attr_elem = measure.find('attributes')
            if m_attr_elem is not None:
                divisions_elem = m_attr_elem.find('divisions')
                if divisions_elem is not None:
                    divisions = int(divisions_elem.text)

            measure_num = measure.attrib['number']
            # removes non-requested measure
            if measure_num not in ema_measures:
                staves[s].remove(measure)
            # requested measure
            else:
                ema_measure = ema_measures[measure_num]
                # if stave in selection, choose beats
                if s+1 in ema_measure.staves:
                    beats = ema_measure.staves[s + 1]
                    time = 0
                    notes = measure.findall("note")
                    for n in range(len(notes)):
                        note = notes[n]
                        duration = int(note.find("duration").text)
                        if (time // divisions) + 1 not in beats:
                            convert_to_rest(note)
                        time += duration
                # else, blank measure
                else:
                    for note in measure.findall("note"):
                        convert_to_rest(note)
                # increment m after processing a requested measure
                m += 1
    return tree
