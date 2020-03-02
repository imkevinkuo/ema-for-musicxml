import xml.etree.ElementTree as ET
from ema2.emaexpfull import EmaExpFull, ema_to_list


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
    staves = tree.findall("part")
    for s in range(len(staves)):
        process_stave(ema_exp_full, s+1, staves[s])
    remove_blank_staves(tree, ema_exp_full)
    return tree


def process_stave(ema_exp_full, staff_num, measures):
    """ Traverse one stave and edit it according to the EmaExpFull. """
    selection = ema_exp_full.selection
    m = 0
    attrib = {}
    insert_attrib = False
    while m < len(measures):
        measure = measures[m]
        measure_num = measure.attrib['number']

        m_attr_elem = measure.find('attributes')
        if m_attr_elem:
            if measure_num in selection:
                insert_attrib = False
            # There are new attributes but this measure was not selected. Insert on next selected measure.
            else:
                insert_attrib = True
                attrib = elem_to_dict(m_attr_elem)

        # make selection
        if measure_num in selection:
            if insert_attrib:
                measure.insert(0, dict_to_elem('attributes', attrib))
                insert_attrib = False

            ema_measure = selection[measure_num]
            if staff_num in ema_measure:
                numer = int(attrib['time']['beats']['text'])
                denom = int(attrib['time']['beat-type']['text'])
                beat_factor = numer / denom
                divisions = int(attrib['divisions']['text'])
                beats = ema_to_list(ema_measure[staff_num], {'start': 1, 'end': numer})
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


def elem_to_dict(elem):
    d = {'text': elem.text, 'tail': elem.tail}
    if elem:
        for child in elem:
            d[child.tag] = elem_to_dict(child)
    return d


def dict_to_elem(name, d):
    elem = ET.Element(name)
    elem.text = d['text']
    elem.tail = d['tail']
    for key in d:
        if key != 'text' and key != 'tail':
            elem.append(dict_to_elem(key, d[key]))
    return elem
