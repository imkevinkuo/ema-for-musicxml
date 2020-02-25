import xml.etree.ElementTree as ET
from ema2.emaexpfull import EmaExpFull


def convert_to_rest(note: ET.Element):
    """ Remove all note-associated attributes, (i.e. keep duration, type, voice, and lyrics). """
    note_remove = ["pitch", "stem"]
    for r in note_remove:
        note_elem = note.find(r)
        if note_elem:
            note.remove(note_elem)
    note.insert(0, ET.Element("rest"))


# TODO: Make a version for measurewise-XML
def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ For part-wise MusicXML files. """
    selection = ema_exp_full.selection
    staves = tree.findall("part")
    for s in range(len(staves)):
        staff_num = s+1
        # TODO: maybe convert all EmaExp to partwise, then staff check is more time-efficient
        # TODO Dont do that
        # make a check here, if this staff should be included at all
        m = 0
        measures = staves[s]
        divisions = 0
        while m < len(measures):
            measure = measures[m]
            measure_num = measure.attrib['number']

            # detect time signature change
            m_attr_elem = measure.find('attributes')
            if m_attr_elem is not None:
                divisions_elem = m_attr_elem.find('divisions')
                if divisions_elem is not None:
                    divisions = int(divisions_elem.text)

            # make selection
            if measure_num in selection:
                ema_measure = selection[measure_num]
                if staff_num in ema_measure:
                    beats = ema_measure[staff_num]
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
                measures.remove(measure)
    return tree
