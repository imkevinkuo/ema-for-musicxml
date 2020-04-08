import xml.etree.ElementTree as ET
from ema2.emaexp import EmaExp
from ema2.emaexpfull import EmaExpFull, get_score_info_mxl


def slice_score_path(filepath, exp_str):
    tree = ET.parse(filepath)
    emaexp = EmaExp(exp_str)
    emaexp_full = EmaExpFull(get_score_info_mxl(tree), emaexp)
    return slice_score(tree, emaexp_full)


def convert_to_rest(note: ET.Element):
    """ Remove all note-associated attributes, (i.e. keep duration, type, voice, and lyrics). """
    note_remove = ["pitch", "stem"]
    for r in note_remove:
        note_elem = note.find(r)
        if note_elem:
            note.remove(note_elem)
    note.insert(0, ET.Element("rest"))


def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ For part-wise MusicXML files. """
    parts = tree.findall("part")
    current_staff = 1
    for part in parts:
        # process_part returns the number of staves inside that part.
        # E.g. if parts[0] has two staves, then after processing it current_staff should equal 3.
        current_staff += process_part(ema_exp_full, current_staff, part)
    remove_blank_staves(tree, ema_exp_full)
    return tree


# TODO: HANDLE MULTIPLE STAVES WITHIN ONE PART
# TODO: keep track of selected element ids
# if does not have id, get an xpath, either way both of them are a string
def process_part(ema_exp_full, starting_staff, measures):
    """ Traverse one part and edit it according to the EmaExpFull. """
    selection = ema_exp_full.selection
    m = 0
    attrib = {}
    insert_attrib = {}
    staves_in_part = 1
    while m < len(measures):
        measure: ET.Element = measures[m]
        measure_num = measure.attrib['number']

        # Keep track of attribute changes - e.g. if we don't select a measure with a time sig change,
        # we would still want the new time sig to be reflected in following measures.
        m_attr_elem: ET.Element = measure.find('attributes')
        if m_attr_elem:
            measure_attrib = elem_to_dict(m_attr_elem)
            for key in measure_attrib:
                attrib[key] = measure_attrib[key]
                if measure_num not in selection:
                    insert_attrib[key] = measure_attrib[key]
            # For handling parts that contain multiple staves
            if "staves" in measure_attrib:
                staves_in_part = int(measure_attrib["staves"]['text'])

        # make selection
        if measure_num in selection:
            staff_num = starting_staff
            # print("In measure", measure_num, "staff", staff_num)
            if insert_attrib:  # True if insert_attrib != {}
                # Need to check if this measure already has attributes
                if m_attr_elem:
                    insert_or_combine(measure, dict_to_elem('attributes', insert_attrib))
                else:
                    measure.insert(0, dict_to_elem('attributes', insert_attrib))
                insert_attrib = {}

            # Setup for traversing the measure - <backup> elements mean multiple staves
            ema_measure = selection[measure_num]
            if staff_num in ema_measure:
                ema_beats = ema_measure[staff_num]  # list of EmaRange
            else:
                ema_beats = []
            divisions = int(attrib['divisions']['text'])
            ema_index = 0
            curr_time = 0.0
            # TODO: Handle cut time?
            # TODO: sort beat selection by starting time - do not allow overlapping ranges
            # TODO: Completeness
            for child in measure:
                # print(measure_num, staff_num, curr_time, child.tag)
                if child.tag == 'note':
                    if ema_index < len(ema_beats):
                        # Get note duration, current EmaRange, and current beat
                        beat_range = ema_beats[ema_index]
                        curr_beat = 1.0 + (curr_time / divisions)
                        # If the note starts after the EmaRange end, go to the next EmaRange.
                        if beat_range.end != 'end':
                            while curr_beat > beat_range.end + 0.01 and ema_index < len(ema_beats) - 1:
                                ema_index += 1
                                beat_range = ema_beats[ema_index]
                        # Check if the note starts inside of the EmaRange.
                        if beat_in_range(curr_beat, beat_range):
                            # print(f"Selected beat {curr_beat} in staff {staff_num}, measure {measure_num}")
                            pass  # do nothing
                        else:
                            convert_to_rest(child)
                        duration = int(child.find("duration").text)
                        curr_time += duration
                elif child.tag == 'backup':
                    staff_num += 1
                    staves_in_part += 1
                    if staff_num in ema_measure:
                        ema_beats = ema_measure[staff_num]  # list of EmaRange
                    else:
                        ema_beats = []
                    ema_index = 0
                    duration = int(child.find("duration").text)
                    curr_time -= duration
            m += 1
        else:
            measures.remove(measure)
    # TODO: Last measure in stave should have single "\n" tail, not two - not sure if this will cause any problems.
    return staves_in_part


def beat_in_range(beat, ema_range):
    s = ema_range.start == 'start' or beat >= ema_range.start
    e = ema_range.end == 'end' or beat <= ema_range.end
    return s and e


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


# Used to convert the 'attributes' element to a dict for easy value access during beat slicing.
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


def insert_or_combine(parent, child):
    """ Inserts child into parent. If parent already has an inner element with
        the same tag as child, combine them instead (without overwriting parent). """
    sibling = parent.find(child.tag)
    if sibling is None:
        parent.insert(0, child)
    else:
        for inner_child in child:
            insert_or_combine(sibling, inner_child)