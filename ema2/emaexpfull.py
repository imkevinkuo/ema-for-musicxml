import xml.etree.ElementTree as ET
from ema2.emaexp import EmaExp


class EmaExpFull(object):
    """ Represents an EMA expression after evaluation of 'start/end' tokens and expansion of all ranges.

        EMA does not require us to store the "order" of requested measures; just which measures are requested.
        Our XML slicing will preserve the existing order since we will simply delete non-requested measures.
    """

    def __init__(self, score_info: dict, ema_exp: EmaExp):
        # TODO: If score_info is a str, treat it as filepath to musicxml and use get_score_info?
        self.score_info = score_info
        self.selection = expand_ema_exp(score_info, ema_exp)
        self.completeness = ema_exp.completeness


def expand_ema_exp(score_info, ema_exp):
    """ Converts an EmaExpression to a List[EmaMeasure]. We use a measure-wise representation.
        selection[measure #] = dict: {staff #: set(requested beats)}
        selection[measure #][staff #] = set(requested beats)
    """
    selection = {}
    measure_nums = ema_to_list(ema_exp.mm_ranges, score_info['measure'])
    for m in range(len(measure_nums)):
        measure_num = str(measure_nums[m])

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

            staff_beats = ema_exp.bt_ranges[m2][s2]  # We will run ema_to_list while slicing.

            # Insert beats into selection
            if measure_num not in selection:
                selection[measure_num] = {stave_num: staff_beats}
            else:
                sel_staves = selection[measure_num]
                if stave_num in sel_staves:
                    for ema_range in staff_beats:
                        sel_staves[stave_num].append(ema_range)
                else:
                    sel_staves[stave_num] = staff_beats
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
# TODO: Don't use special handling for measure numbers - just treat first measure as 1, even if there is a pickup
def get_score_info_mxl(tree: ET.ElementTree):
    score_info = {'measure': {},
                  'staff': {
                      'start': 1
                  }}
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
    score_info['measure']['start'] = int(measures[0].attrib['number'])
    score_info['measure']['end'] = int(measures[-1].attrib['number'])
    score_info['staff']['end'] = total_staves
    return score_info
