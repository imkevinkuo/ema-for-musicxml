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
# TODO: preserve inner-measure attributes like clef
def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ For part-wise MusicXML files. """
    staves = tree.findall("part")
    for s in range(len(staves)):
        process_stave(ema_exp_full, s+1, staves[s])
    remove_blank_staves(tree, ema_exp_full)
    return tree


def process_stave(ema_exp_full, staff_num, measures):
    """ Traverse one stave and edit it according to the EmaExpFull. """
    selection = ema_exp_full.selection
    divisions = 0
    m = 0
    while m < len(measures):
        measure = measures[m]
        measure_num = measure.attrib['number']

        # TODO: keep track of ALL attributes across measures
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
                time_sig = ema_exp_full.score_info['beat']['end'][measure_num]
                beat_factor = time_sig[0] / time_sig[1]

                beats = ema_measure[staff_num]
                time = 0
                for note in measure.findall("note"):
                    if (time // (beat_factor * divisions)) + 1 not in beats:
                        convert_to_rest(note)
                    duration = int(note.find("duration").text)
                    time += duration
            else:
                for note in measure.findall("note"):
                    convert_to_rest(note)
            m += 1
        else:
            measures.remove(measure)


def remove_blank_staves(tree, ema_exp_full):
    selected_staves = ema_exp_full.selected_staves
    staves = tree.findall("part")
    partlist = tree.find("part-list")
    scoreparts = partlist.findall("score-part")
    for s in range(len(staves) - 1, -1, -1):
        staff_num = s + 1
        if staff_num not in selected_staves:
            tree.getroot().remove(staves[s])
            partlist.remove(scoreparts[s])
