import xml.etree.ElementTree as ET
from ema2.emaexp import EmaExp
from ema2.emaexpfull import EmaExpFull, get_score_info_mxl


NOTE_TYPES = {1: 'whole',
              2: 'half',
              4: 'quarter',
              8: 'eighth',
              16: 'sixteenth'}

SCALING_CONSTANT = 32


# slice_score_path("../tst/data/ema_test_in.xml", "1/1/@all").write("../tst/data/ema_test_out.xml")
# slice_score_path("../tst/data/scores/DC0101.xml", "2,3/1+2,3+4/@all")
def slice_score_path(filepath, exp_str):
    tree = ET.parse(filepath)
    emaexp = EmaExp(exp_str)
    emaexp_full = EmaExpFull(get_score_info_mxl(tree), emaexp)
    return slice_score(tree, emaexp_full)


def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ High-level function for part-wise MusicXML files. """
    parts = tree.findall("part")
    current_staff = 1
    for part in parts:
        # process_part returns the number of staves inside that part.
        # E.g. if parts[0] has two staves, then after processing it current_staff should equal 3.
        current_staff += process_part(ema_exp_full, current_staff, part)
    # TODO: If we only select from a single staff in a part that has two staves, do we keep the other blank staff?
    # TODO: We should in general remove unselects parts though
    # remove_unselected_staves(tree)
    return tree


# TODO: keep track of selected element ids
# if does not have id, get an xpath, either way both of them are a string
def process_part(ema_exp_full, starting_staff, measures):
    """ Traverse one part and edit it according to the EmaExpFull. """
    attrib = {}
    insert_attrib = {}
    staves_in_part = 1
    measure_idx = 0
    measure_num = 1
    selection = ema_exp_full.selection
    completeness = ema_exp_full.completeness
    while measure_idx < len(measures):
        measure: ET.Element = measures[measure_idx]

        # Keep track of attribute changes - e.g. if we don't select a measure with a time sig change,
        # we would still want the new time sig to be reflected in the next selected measure.
        m_attr_elem: ET.Element = measure.find('attributes')
        if m_attr_elem is not None:
            measure_attrib = elem_to_dict(m_attr_elem)
            # Scaling all divisions by 2048
            measure_attrib["divisions"][0]["text"] = str(int(measure_attrib["divisions"][0]["text"])*SCALING_CONSTANT)
            for key in measure_attrib:
                attrib[key] = measure_attrib[key]
                insert_attrib[key] = measure_attrib[key]
            # For handling parts that contain multiple staves
            if "staves" in measure_attrib:
                staves_in_part = int(measure_attrib["staves"][0]['text'])

        # Scale all notes by 2048
        for child in measure:
            duration = child.find("duration")
            if duration is not None:
                duration.text = str(int(duration.text)*SCALING_CONSTANT)

        if measure_num in selection:
            # print("In measure", measure_num, "starting staff", starting_staff)
            select_beats(measure, selection[measure_num], starting_staff, attrib, completeness)
            measure_idx += 1

            # We have some attributes we want to insert into the next selected measure
            if insert_attrib:
                if m_attr_elem:
                    measure.remove(m_attr_elem)
                measure.insert(0, dict_to_elem('attributes', insert_attrib))
                insert_attrib = {}
        else:
            measures.remove(measure)
        measure_num += 1
    return staves_in_part


def select_beats(measure, ema_measure, starting_staff, attrib, completeness=None):
    staff_num = starting_staff
    if staff_num in ema_measure:
        ema_beats = ema_measure[staff_num]  # list of EmaRange
    else:
        ema_beats = []
    divisions = int(attrib['divisions'][0]['text'])
    curr_time = 0
    # TODO: Check cut time
    # TODO: Completeness
    # For handling completeness insertion
    child_index = 0
    for child in measure:
        duration_elem = child.find("duration")
        duration = int(duration_elem.text) if duration_elem is not None else None
        if child.tag == 'note':
            if (child.find("rest")) is None:
                # Check if note is inside any of the ema_ranges for this measure+staff.
                # Just check every range, shouldn't be computationally expensive
                matched_ema_range = None
                for beat_range in ema_beats:
                    time_range = beat_range.convert_to_time(divisions)
                    if note_in_range(curr_time, duration, time_range):
                        matched_ema_range = time_range
                        print(f"Selected note @ time {curr_time}, staff {staff_num}")

                if matched_ema_range:
                    if completeness == 'cut':
                        trim_note(measure, child, child_index, curr_time, duration, matched_ema_range, divisions)
                else:
                    remove_from_selection(child)
            curr_time += duration
        elif child.tag == 'backup':
            staff_num += 1
            ema_beats = ema_measure.get(staff_num, [])  # Defaults to [] if not selected
            curr_time -= duration
        child_index += 1


def trim_note(measure, child, child_index, start_time, duration, matched_ema_range, divisions):
    """ Trims the note down to the matched_ema_range. Used for completeness == 'cut'. """
    end_time = start_time + duration
    s = matched_ema_range.start == 'start' or matched_ema_range.start <= start_time
    e = matched_ema_range.end == 'end' or matched_ema_range.end >= end_time
    # If the note overflows outside the matched_ema_range, we need to trim and replace the open spaces with rests.
    trimmed_start, trimmed_end = start_time, start_time + duration
    print("Starting note length:", trimmed_end - trimmed_start)
    if not s:
        trimmed_start = matched_ema_range.start
        rest_length = matched_ema_range.start - start_time
        rest = create_rest_element(rest_length, child)
        measure.insert(child_index, rest)
        print("Trimmed note start, new length", trimmed_end - trimmed_start)
    if not e:
        trimmed_end = matched_ema_range.end
        rest_length = end_time - matched_ema_range.end
        # child.tail is '\n' + some spaces
        rest = create_rest_element(rest_length, child, divisions)
        measure.insert(child_index + 1, rest)
        print("Trimmed note end, new length", trimmed_end - trimmed_start, "rest length", rest_length)
    if s or e:
        new_duration = int(trimmed_end - trimmed_start)
        child.find("duration").text = str(new_duration)
        child.find("type").text = NOTE_TYPES[int(4 * divisions / new_duration)]


def create_rest_element(rest_length, orig_note, divisions):
    """  rest_length must be an int. """
    # TODO: Change subelements: type (quarter, eighth, etc.), time-modification, stem, notations, etc..
    # Copy original note, then change subelements
    orig_note_dict = elem_to_dict(orig_note)
    # orig_note_dict['type']['text'] =
    orig_note_dict['duration'][0]['text'] = str(int(rest_length))
    orig_note_dict['type'][0]['text'] = NOTE_TYPES[int(4*divisions/rest_length)]
    note_elem = dict_to_elem('note', orig_note_dict, len(orig_note.tail) - 1)
    return note_elem


# Used to convert the 'attributes' element to a dict for easy value access during beat slicing.
# This is a dict of str:list. Each list contains more dicts like this.
# The reason we have a list of dicts (as opposed to a single dict) is because we index by tag name,
# but we can have multiple of the same tag as children (e.g. multiple <clef>s in <attributes>)
def elem_to_dict(elem):
    d = {'text': elem.text, 'tail': elem.tail, 'attrib': elem.attrib}
    if elem:
        for child in elem:
            if child.tag not in d:
                d[child.tag] = []
            d[child.tag].append(elem_to_dict(child))
    return d


def dict_to_elem(name, d, indent=0):
    elem = ET.Element(name)
    exclude_keys = ['text', 'tail', 'attrib']
    elem.text = d.get('text', '\n' + ' '*(indent+2))
    elem.tail = d.get('tail', "\n" + ' '*indent)
    elem.attrib = d.get('attrib')
    for key in d:
        if key not in exclude_keys:
            for child_dict in d[key]:
                elem.append(dict_to_elem(key, child_dict, indent + 2))
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


def note_in_range(start_time, duration, ema_range):
    """ Checks if the beat at given start_time and duration overlaps with the ema_range.
    Notes will have a definite length, unlike EMA ranges, so check if EMA_range intersects with note. """
    end_time = start_time + duration
    # Assume we don't need to deal with ema_range.end == 'start' or ema_range.start == 'end'
    r1 = ema_range.end == 'end' or start_time <= ema_range.end  # Beat starts before range end
    r2 = ema_range.start == 'start' or ema_range.start < end_time  # Range starts before beat end
    return r1 and r2


def remove_from_selection(note: ET.Element):
    """ Process a non-selected note (i.e. convert to rest, keep duration/type/voice, remove pitch/stem/lyrics). """
    note_remove = ["pitch", "stem", "lyric"]
    for r in note_remove:
        note_elem = note.find(r)
        if note_elem:
            note.remove(note_elem)
    note.insert(0, ET.Element("rest"))


def remove_unselected_staves(tree, selected_staves):
    staves = tree.findall("part")
    partlist = tree.find("part-list")
    scoreparts = partlist.findall("score-part")
    for s in range(len(staves) - 1, -1, -1):
        staff_num = s + 1
        if staff_num not in selected_staves:
            tree.getroot().remove(staves[s])
            partlist.remove(scoreparts[s])