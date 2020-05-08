import xml.etree.ElementTree as ET
from emaMXL.emaexp import EmaExp, EmaRange


class EmaExpFull(object):
    """ Represents an EMA expression after evaluation of 'start/end' tokens and expansion of all ranges.

        EMA does not require us to store the "order" of requested measures; just which measures are requested.
        Our XML slicing will preserve the existing order since we will simply delete non-requested measures.
    """

    def __init__(self, score_info: dict, ema_exp: EmaExp):
        self.score_info = score_info
        self.selection = expand_ema_exp(score_info, ema_exp)
        self.completeness = ema_exp.completeness


class EmaRangeFull(object):
    """ Represents a (start, end) pair given in an EMA expression, with 'start', 'end', and 'all' evaluated. """
    def __init__(self, start, end):
        self.start = start
        self.end = end

    # TODO: 'start' always evaluates to 1, but 'end' varies with time signature. Finding the number of beats in
    #  every measure would be useful for algebraic operations on EmaRangeFull, but would require traversal + storage.
    @classmethod
    def from_ema_range(cls, ema_range):
        start = ema_range.start
        if start == 'start' or start == 'all':
            start = 1
        end = ema_range.end
        if end == 'all':
            end = 'end'
        return cls(start, end)

    def scale_beat(self, factor):
        """ We round values to the closest integer - this means we are snapping selection beats to the closest
        subdivision, which is specified by the MusicXML. """
        time_start = self.start
        time_end = self.end
        if time_start != 'start':
            time_start = round((self.start - 1)*factor, 0)
        if time_end != 'end':
            time_end = round((self.end - 1)*factor, 0)
        if isinstance(time_start, float) and isinstance(time_end, float) and time_end < time_start:
            print(f"Warning: beat-to-time conversion produced end {time_end} before start {time_start}")
            time_end = time_start
        return EmaRangeFull(time_start, time_end)

    # TODO: Defining add and mul would be convenient. But requires 'end' to already be evaluated to a number
    #  This would enable usage like EmaRangeFull(1, 3)*2 + 1 = EmaRangeFull(3, 7).

    def contains_note(self, start_time, end_time):
        """ Checks if the beat at given start_time and duration overlaps with this EmaRangeFull.

        :param start_time: Start time of the note, in divisions.
        :type start_time: int
        :param end_time: End time of the note, in divisions.
        :type end_time: int
        :return: bool
        """
        r1 = self.end == 'end' or start_time < self.end  # Beat starts before range end
        r2 = self.start < end_time  # Range starts before beat end
        return r1 and r2

    def __str__(self):
        return f"[{self.start} {self.end}]"


def expand_ema_exp(score_info, ema_exp):
    """ Converts an EmaExpression to a List[EmaMeasure]. We use a measure-wise representation.
        selection[measure #][staff #] = List[EmaRangeFull]
    """
    selection = {}
    measure_nums = ema_to_list(ema_exp.mm_ranges, score_info['measure'])
    for m in range(len(measure_nums)):
        measure_num = measure_nums[m]

        # Handle expression like 1-3/@all/... (staff expression mapping to multiple measures)
        m2 = m
        if len(ema_exp.st_ranges) == 1:
            m2 = 0

        stave_nums = ema_to_list(ema_exp.st_ranges[m2], score_info['staff'])
        for s in range(len(stave_nums)):
            stave_num = stave_nums[s]

            # Handle expressions like 1,2/1+2,2+3/@1-2 and 1,2/1+2,2+3/@1-2,@all
            # (single beat expression mapping to multiple staves/measures)
            s2, m2 = s, m
            if len(ema_exp.bt_ranges) == 1:
                m2 = 0
            if len(ema_exp.bt_ranges[m2]) == 1:
                s2 = 0

            # TODO: What happens if user gives a bad/weird request? e.g. overlapping measures, staves, beats, etc.
            staff_beats = ema_exp.bt_ranges[m2][s2]  # List of EmaRanges, specifying beats

            if measure_num not in selection:
                selection[measure_num] = {}
            sel_staves = selection[measure_num]
            if stave_num not in sel_staves:
                sel_staves[stave_num] = []
            for ema_range in staff_beats:
                ema_range_full = EmaRangeFull.from_ema_range(ema_range)
                sel_staves[stave_num].append(ema_range_full)
    return selection


def ema_to_list(ema_range_list, start_end):
    """ Converts a list of EmaRanges to a list of ints.
        :param ema_range_list : List[EmaRange] describing a set of measures, staves, or beats.
        :param start_end      : Dict with keys 'start' and 'end' mapped to values for this evaluation.
        :return ema_list      : List[int] of all values specified in the EmaRanges
    """
    ema_list = []
    for ema_range in ema_range_list:
        start = start_end.get(ema_range.start, ema_range.start)
        end = start_end.get(ema_range.end, ema_range.end)
        ema_list += [x for x in range(start, end + 1)]
    return ema_list


# By-measure attributes are handled during slicing.
# TODO: Maybe we can also store time signature information.
#  we *could* get this info during the slicing but that would make it even more complicated
def get_score_info_mxl(tree: ET.ElementTree):
    score_info = {'measure': {'start': 1},
                  'staff': {'start': 1}}
    # One part may contain multiple staves.
    parts = tree.getroot().findall('part')
    total_staves = 0
    for part in parts:
        part_staves = 1
        for measure in part:
            attributes = measure.find("attributes")
            if attributes is not None:
                staves = attributes.find("staves")
                if staves is not None:
                    part_staves = int(staves.text)
        total_staves += part_staves

    measures = parts[0].findall('measure')
    score_info['measure']['end'] = len(measures)
    score_info['staff']['end'] = total_staves
    return score_info
