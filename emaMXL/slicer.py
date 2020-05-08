import copy
import xml.etree.ElementTree as ET
from emaMXL.emaexp import EmaExp
from emaMXL.emaexpfull import EmaExpFull, get_score_info_mxl


NOTE_TYPES = {1: 'whole',
              2: 'half',
              4: 'quarter',
              8: 'eighth',
              16: '16th',
              32: '32nd',
              64: '64th'}

SCALING_CONSTANT = 1


# slice_score_path("../tst/data/ema_test_in.xml", "1/2/@1-1.5/cut").write("../tst/data/ema_test_out.xml")
# filepath = "../tst/data/ema_test_in.xml"
# exp_str = "1/1/@1/cut"
# tree = ET.parse(filepath)
# emaexp = EmaExp(exp_str)
# emaexp_full = EmaExpFull(get_score_info_mxl(tree), emaexp)
def slice_score_path(filepath, exp_str):
    """ Highest-level selection function; creates a selection from a MusicXML filepath and EMA expression string.

    :param filepath: A filepath to a MusicXML score.
    :type filepath: str
    :param exp_str: A string describing an EMA selection.
    :type exp_str: str
    :return: An ElementTree representing the selection.
    :rtype: ET.ElementTree
    """
    tree = ET.parse(filepath)
    emaexp = EmaExp(exp_str)
    emaexp_full = EmaExpFull(get_score_info_mxl(tree), emaexp)
    return slice_score(tree, emaexp_full)


def slice_score(tree, ema_exp_full):
    """ Executes a selection on an entire score.

    :param tree: MusicXML file loaded with ET
    :type tree: ET.ElementTree
    :param ema_exp_full: EmaExpFull object created by parser.py
    :type ema_exp_full: EmaExpFull
    :return An ElementTree representing the selection.
    """
    parts = tree.findall("part")
    current_staff = 1
    selected_parts = []
    part_idx = 0
    for part in parts:
        staves_in_part, part_in_selection = process_part(ema_exp_full, current_staff, part)
        current_staff += staves_in_part
        if part_in_selection:
            selected_parts.append(part_idx)
        part_idx += 1
    remove_unselected_parts(tree, selected_parts)
    return tree


# TODO: keep track of selected element ids. If elem does not have id, get an xpath.
def process_part(ema_exp_full, starting_staff, measures):
    """ Traverses a single part. Measures are trimmed to those between the start and end measures of the selection.
    Staves are trimmed to only requested staves.

    :param ema_exp_full: EmaExpFull object created by parser.py
    :type ema_exp_full: EmaExpFull
    :param starting_staff: The lowest staff number this part contains
    :type starting_staff: int
    :param measures: An ET.Element with tag "part"; contains the measures to be processed
    :type measures: ET.Element
    :return: The number of staves contained in this part  (MusicXML supports multiple staves per part),
             and a boolean indicating if any beats were selected in this part.
    :rtype: int, bool
    """
    attrib = {}
    insert_attrib = {}
    staves_in_part = 1
    measure_idx = 0
    measure_num = 1
    selection = ema_exp_full.selection
    completeness = ema_exp_full.completeness
    part_in_selection = False
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
            part_in_selection = True
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
    return staves_in_part, part_in_selection


def select_beats(measure, ema_measure, starting_staff, attrib, completeness=None):
    """ Traverses the notes in the measure and converts non-selected notes into rests.

    :param measure: An ET.Element with tag "measure"; contains the notes to be processed
    :param ema_measure: ET.Element
    :param starting_staff: The starting staff number - multiple staves can be contained in a MusicXML measure.
    :param attrib: A nested dict representation of the current measure attributes element.
                    The key (tag) maps to a list of elements with that tag (each with its own dictionary).
    :type attrib: dict[str, list[dict]]
    :param completeness: Additional selection argument described in EMA API.
    :type completeness: str
    :return: Does not return an object; edits the inputted measure.
    :rtype: None
    """
    staff_num = starting_staff
    if staff_num in ema_measure:
        ema_beats = ema_measure[staff_num]  # list of EmaRange
    else:
        ema_beats = []
    divisions = int(attrib['divisions'][0]['text'])
    curr_time = 0
    # For handling completeness insertion
    child_index = 0
    for child in measure:
        duration_elem = child.find("duration")
        duration = int(duration_elem.text) if duration_elem is not None else None
        if child.tag == 'note':
            if (child.find("rest")) is None:
                # Check if note is inside any of the ema_ranges for this measure & staff.
                matched_ema_range = None
                for beat_range in ema_beats:
                    time_range = beat_range.scale_beat(divisions)
                    if time_range.contains_note(curr_time, curr_time + duration):
                        matched_ema_range = time_range
                        print(f"Selected note @ time {curr_time}, staff {staff_num}")
                        print(f"Beat -> Division Range: {beat_range} -> {time_range}")

                if matched_ema_range:
                    # If note falls inside the range, we want to keep it.
                    # If 'cut' is specified, then we trim the note as needed.
                    if completeness == 'cut':
                        trim_note(measure, child, child_index, curr_time, duration, matched_ema_range, divisions)
                else:
                    # 'raw' behavior here will remove instead of converting to rest
                    remove_from_selection(child)
            curr_time += duration
        elif child.tag == 'backup':
            staff_num += 1
            ema_beats = ema_measure.get(staff_num, [])  # Defaults to [] if not selected
            curr_time -= duration
        child_index += 1


def trim_note(measure, note, note_index, start_time, duration, matched_ema_range, divisions):
    """ Trims a note down to the matched_ema_range and fills in spaces with rests. Used for completeness == 'cut'.

    :param measure: The measure element containing the note.
    :type measure: ET.Element
    :param note: The note element to be trimmed.
    :type note: ET.Element
    :param note_index: The index of the note element within the measure element.
    :type note_index: int
    :param start_time: The start time of the note, in divisions.
    :type start_time: int
    :param duration: The duration of the note, in divisions.
    :type duration: int
    :param matched_ema_range: The beat selection requested by the user.
    :type matched_ema_range: ema2.emaexp.EmaRange
    :param divisions: The number of divisions given to a quarter note, as provided by measure attributes.
    :type divisions: int
    :return: None
    """
    end_time = start_time + duration
    s = matched_ema_range.start <= start_time
    e = matched_ema_range.end == 'end' or matched_ema_range.end >= end_time
    # If the note overflows outside the matched_ema_range, we need to trim and replace the open spaces with rests.
    trimmed_start, trimmed_end = start_time, start_time + duration
    print("Starting note length:", trimmed_end - trimmed_start)
    # TODO: Instead of directly setting rest length, split into unit lengths
    #  e.g. eighth + sixteenth rather than dotted eighth. when should this happen vs. combined?
    if not s:
        trimmed_start = matched_ema_range.start
        rest_length = matched_ema_range.start - start_time
        rest = create_rest_element(note, rest_length, divisions)
        measure.insert(note_index, rest)
    if not e:
        trimmed_end = matched_ema_range.end
        rest_length = end_time - matched_ema_range.end
        rest = create_rest_element(note, rest_length, divisions)
        measure.insert(note_index + 1, rest)
    if s or e:
        new_duration = int(trimmed_end - trimmed_start)
        set_note_duration(note, new_duration, divisions)


def set_note_duration(note, duration, divisions):
    """ Sets a note's duration and adjusts other attributes (type, time-modification, etc.) accordingly.

    :param note: The note trimmed by completeness = 'cut'
    :type note: ET.Element
    :param duration: Length of the rest, in divisions.
    :type duration: int
    :param divisions: The number of divisions per quarter note, specified by measure attributes.
    :type divisions: int
    :return: None
    """
    # TODO: Need to handle more subelements: stem, notations, etc..
    # Changes the <type> element to the correct note type and handles time-modification (tuplets) if present.
    note_denom = int(4 * divisions / duration)
    # 1-1.66 shouldn't cause issues but instead scraps the note
    #
    # 1-1.167 error on 3 8 - attempts to make dotted eighth rest.
    time_mod: ET.Element = note.find('time-modification')
    if time_mod is not None:
        actual_notes = int(time_mod.find('actual-notes').text)
        normal_notes = int(time_mod.find('normal-notes').text)
        note_denom = note_denom * normal_notes / actual_notes

        normal_type = time_mod.find('normal-type')
        if normal_type is None:
            normal_type = ET.Element('normal-type')
            time_mod.append(normal_type)
        normal_type.text = note.find('type').text

    # Set child element values.
    note.find('duration').text = str(int(duration))
    if note_denom in NOTE_TYPES:
        note.find('type').text = NOTE_TYPES[note_denom]
    elif int(note_denom * 3 / 2) in NOTE_TYPES:
        note_denom = int(note_denom * 3 / 2)
        note.find('type').text = NOTE_TYPES[note_denom]
        type_index = list(note).index(note.find('type'))
        note.insert(type_index + 1, ET.Element("dot"))

    print(f"Set type: {NOTE_TYPES[note_denom]}, duration: {duration}")


def create_rest_element(note, duration, divisions):
    """ Creates the filler rests for 'cut' completeness; works off of a copy of the cut note to preserve tuplet data.

    :param note: The note trimmed by completeness = 'cut'
    :type note: ET.Element
    :param duration: Length of the rest, in divisions.
    :type duration: int
    :param divisions: The number of divisions per quarter note, specified by measure attributes.
    :type divisions: int
    :return: The note element with an inner "rest" tag.
    :rtype: ET.Element
    """
    new_note = copy.deepcopy(note)

    if new_note.find("pitch") is not None:
        new_note.remove(new_note.find("pitch"))

    if new_note.find("notations") is not None:
        new_note.remove(new_note.find("notations"))

    new_note.insert(0, ET.Element("rest"))
    set_note_duration(new_note, duration, divisions)
    return new_note


def elem_to_dict(elem):
    """ Used to convert the 'attributes' element to a dict for easy value access during beat slicing.
    This is a dict of str:list. Each list contains more dicts like this.
    The reason we have a list of dicts (as opposed to a single dict) is because we index by tag name,
    but we can have multiple of the same tag as children (e.g. multiple <clef>s in <attributes>)

    :param elem: The element to convert.
    :type elem: ET.Element
    :return: A nested dict representation of the element.
                    The key (tag) maps to a list of elements with that tag (each with its own dictionary).
    :rtype: dict[str, list[dict]]
    """
    d = {'text': elem.text, 'tail': elem.tail, 'attrib': elem.attrib}
    if elem:
        for child in elem:
            if child.tag not in d:
                d[child.tag] = []
            d[child.tag].append(elem_to_dict(child))
    return d


def dict_to_elem(name, d, indent=0):
    """ Inverse function for elem_to_dict. Allows a custom indentation for the XML test.

    :param name: The tag of the element to create.
    :type name: str
    :param d: The dictionary to convert into an element.
    :type d: dict[str, list[dict]]
    :param indent: The number of spaces to indent the text by per level.
    :type indent: int
    :return: An element with inner elements specified by d.
    :rtype: ET.Element
    """
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


# def insert_or_combine(parent, child):
#     """ Inserts child into parent. If an inner element of parent has the same tag as child, they are combined.
# 
#     :param parent:
#     :param child:
#     :return:
#     """
#     sibling = parent.find(child.tag)
#     if sibling is None:
#         parent.insert(0, child)
#     else:
#         for inner_child in child:
#             insert_or_combine(sibling, inner_child)


def remove_from_selection(note: ET.Element):
    """ Process a non-selected note (i.e. convert to rest, keep duration/type/voice, remove pitch/stem/lyrics).

    :param note: The element to be removed.
    :type note: ET.Element
    :return: None
    """
    # TODO: Slurs and hairpins
    note_remove = ["pitch", "stem", "lyric"]
    for r in note_remove:
        note_elem = note.find(r)
        if note_elem:
            note.remove(note_elem)
    note.insert(0, ET.Element("rest"))


def remove_unselected_parts(tree, selected_parts):
    """ Removes all non-selected parts (both the <score-part> and the <part> elements) from the score.

    :param tree: The ElementTree representing the score.
    :type tree: ET.ElementTree
    :param selected_parts: The selected part numbers.
    :type selected_parts: List[int]
    :return: None
    """
    parts = tree.findall("part")
    partlist = tree.find("part-list")
    scoreparts = partlist.findall("score-part")
    for s in range(len(parts) - 1, -1, -1):
        if s not in selected_parts:
            tree.getroot().remove(parts[s])
            partlist.remove(scoreparts[s])
