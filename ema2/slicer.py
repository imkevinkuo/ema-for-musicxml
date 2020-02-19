import xml.etree.ElementTree as ET
from ema2.emaexpfull import EmaExpFull


def convert_to_rest(note: ET.Element):
    # remove everything that isn't duration, type, voice, or lyrics
    note_remove = ["pitch", "stem"]
    for r in note_remove:
        note_elem = note.find(r)
        if note_elem:
            note.remove(note_elem)
    note.insert(0, ET.Element("rest"))


def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ For part-wise MusicXML files. """
    ema_measures = ema_exp_full.selection
    staves = tree.findall("part")
    for s in range(len(staves)):
        m = 0
        divisions = 0
        while m < len(staves[s]):
            measure = staves[s][m]
            measure_num = measure.attrib['number']

            # detect time signature change
            m_attr_elem = measure.find('attributes')
            if m_attr_elem is not None:
                divisions_elem = m_attr_elem.find('divisions')
                if divisions_elem is not None:
                    divisions = int(divisions_elem.text)

            if measure_num in ema_measures:
                ema_measure = ema_measures[measure_num]
                if s+1 in ema_measure.staves:
                    beats = ema_measure.staves[s+1]
                    time = 0
                    for note in measure.findall("note"):
                        if (time // divisions) + 1 not in beats:
                            convert_to_rest(note)
                        duration = int(note.find("duration").text)
                        time += duration
                else:
                    for note in measure.findall("note"):
                        convert_to_rest(note)
                m += 1
            else:
                staves[s].remove(measure)
    return tree
