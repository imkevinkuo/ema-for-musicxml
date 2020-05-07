import xml.etree.ElementTree as ET
from ema2.emaexp import EmaExp
from ema2.emaexpfull import EmaExpFull, get_score_info_mxl


NOTE_TYPES = {1: 'whole',
              2: 'half',
              4: 'quarter',
              8: 'eighth',
              16: 'sixteenth'}

SCALING_CONSTANT = 512


# slice_score_path("../tst/data/ema_test_in_2.xml", "1/2/@1-1.5/cut").write("../tst/data/ema_test_out.xml")
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
                # Check if note is inside any of the ema_ranges for this measure+staff.
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
    s = matched_ema_range.start == 'start' or matched_ema_range.start <= start_time
    e = matched_ema_range.end == 'end' or matched_ema_range.end >= end_time
    # If the note overflows outside the matched_ema_range, we need to trim and replace the open spaces with rests.
    trimmed_start, trimmed_end = start_time, start_time + duration
    print("Starting note length:", trimmed_end - trimmed_start)
    if not s:
        trimmed_start = matched_ema_range.start
        rest_length = matched_ema_range.start - start_time
        rest = create_rest_element(rest_length, note)
        measure.insert(note_index, rest)
        print("Trimmed note start, new length", trimmed_end - trimmed_start)
    if not e:
        trimmed_end = matched_ema_range.end
        rest_length = end_time - matched_ema_range.end
        # child.tail is '\n' + some spaces
        rest = create_rest_element(rest_length, note, divisions)
        measure.insert(note_index + 1, rest)
        print("Trimmed note end, new length", trimmed_end - trimmed_start, "rest length", rest_length)
    if s or e:
        new_duration = int(trimmed_end - trimmed_start)
        note.find("duration").text = str(new_duration)
        note.find("type").text = NOTE_TYPES[int(4 * divisions / new_duration)]


def create_rest_element(rest_length, orig_note, divisions):
    """ Takes a trimmed note and creates the rest elements that will fill in the space created by trimming.

    :param rest_length: Length of the rest, in divisions.
    :type rest_length: int
    :param orig_note: The note trimmed by completeness = 'cut'
    :type orig_note: ET.Element
    :param divisions: The number of divisions per quarter note, specified by measure attributes.
    :type divisions: int
    :return: The note element with an inner "rest" tag.
    :rtype: ET.Element
    """
    # TODO: Need to handle subelements: type (quarter, eighth, etc.), time-modification, stem, notations, etc..
    # Copy original note, then change subelements
    orig_note_dict = elem_to_dict(orig_note)
    # orig_note_dict['type']['text'] =
    orig_note_dict['duration'][0]['text'] = str(int(rest_length))
    orig_note_dict['type'][0]['text'] = NOTE_TYPES[int(4*divisions/rest_length)]
    note_elem = dict_to_elem('note', orig_note_dict, len(orig_note.tail) - 1)
    return note_elem


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


def insert_or_combine(parent, child):
    """ Inserts child into parent. If an inner element of parent has the same tag as child, they are combined.

    :param parent: 
    :param child: 
    :return: 
    """
    sibling = parent.find(child.tag)
    if sibling is None:
        parent.insert(0, child)
    else:
        for inner_child in child:
            insert_or_combine(sibling, inner_child)


def note_in_range(start_time, duration, ema_range):
    """ Checks if the beat at given start_time and duration overlaps with the ema_range.

    :param start_time: Starting time of the note, in divisions.
    :type start_time: int
    :param duration: Duration of the note, in divisions.
    :type duration: int
    :param ema_range: The EMA range requested by the user, converted into divisions.
    :type ema_range: ema2.emaexp.EmaRange
    :return: bool
    """
    end_time = start_time + duration
    # Assume we don't need to deal with ema_range.end == 'start' or ema_range.start == 'end'
    r1 = ema_range.end == 'end' or start_time <= ema_range.end  # Beat starts before range end
    r2 = ema_range.start == 'start' or ema_range.start < end_time  # Range starts before beat end
    return r1 and r2


def remove_from_selection(note: ET.Element):
    """ Process a non-selected note (i.e. convert to rest, keep duration/type/voice, remove pitch/stem/lyrics).

    :param note: The element to be removed.
    :type note: ET.Element
    :return: None
    """
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
