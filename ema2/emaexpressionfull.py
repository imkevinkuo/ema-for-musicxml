from typing import List
from music21 import stream
from xml.dom import minidom

from ema2.emaexpression import EmaExpression


class EmaExpressionFull(object):
    """ Represents an EMA expression after evaluation of 'start/end' tokens and expansion of all ranges. """

    def __init__(self, score_info: dict, ema_exp: EmaExpression):
        self.selection = expand_ema_exp(score_info, ema_exp)  # list of EmaMeasure


class EmaStaff(object):
    def __init__(self, staff: int, beats: List[int] = []):
        self.staff = staff
        self.beats = beats


class EmaMeasure(object):
    def __init__(self, measure: int, staves: List[EmaStaff] = []):
        self.measure = measure
        self.staves = staves


def expand_ema_exp(score_info: dict, ema_exp: EmaExpression):
    ema_measures = []
    measure_nums = ema_to_list(ema_exp.mm_ranges, score_info, 'measure')
    for m in range(len(measure_nums)):
        measure_num = measure_nums[m]

        # Handle expression like 1-3/@all/... (staff expression mapping to multiple measures)
        m2 = m
        if len(ema_exp.st_ranges) == 1:
            m2 = 0

        ema_staves = []
        stave_nums = ema_to_list(ema_exp.st_ranges[m2], score_info, 'staff')
        for s in range(len(stave_nums)):
            stave_num = stave_nums[s]

            # Handle expressions like 1,2/1+2,2+3/@1-2 and 1,2/1+2,2+3/@1-2,@all
            # (single beat expression mapping to multiple staves/measures)
            s2, m2 = s, m
            if len(ema_exp.bt_ranges) == 1:
                m2 = 0
            if len(ema_exp.bt_ranges[m2]) == 1:
                s2 = 0

            staff_beats = ema_to_list(ema_exp.bt_ranges[m2][s2], score_info, 'beat', measure_num)
            ema_staves.append(EmaStaff(stave_num, staff_beats))

        ema_measure = EmaMeasure(measure_num, ema_staves)
        ema_measures.append(ema_measure)
    return ema_measures


def get_score_info_m21(score: stream.Score):
    score_info = {'measure': {},
                  'staff': {
                      'start': 1
                  },
                  'beat': {
                      'start': 1
                      # 'end': {measure_num: num_of_beats}
                  }}
    measures = score.parts[0].getElementsByClass(stream.Measure)
    score_info['measure']['start'] = measures[0].measureNumber
    score_info['measure']['end'] = measures[-1].measureNumber
    score_info['staff']['end'] = len(score.parts)
    # PyCharm gives an 'unexpected type' warning because 'start' maps to int while 'end' maps to dict
    score_info['beat']['end'] = {m.measureNumber: m.bestTimeSignature().numerator for m in measures}
    return score_info


def get_score_info_mxl(score: minidom.Document):
    return {}


def ema_to_list(ema_range_list, score_info, unit, measure_num=None):
    """ Converts a list of EmaRanges to a list of ints.
        :param list(EmaRange) ema_range_list: A list of ranges, e.g. measure selections, single-staff beat selections
        :param dict(str, dict) score_info   : Contains 'start'/'end' values for measure, staff, and beat
        :param str unit                     : the type of range we are trying to evaluate ('measure'/'staff'/'beat')
        :param int measure_num              : for unit='beat' only, measure number of this particular beat selection
        :return list(int) ema_list          : expanded values specified in the EmaRanges
    """
    ema_list = []
    for ema_range in ema_range_list:
        start = score_info[unit].get(ema_range.start, ema_range.start)
        if unit == 'beat':
            end = score_info[unit].get(ema_range.end, ema_range.end)
            if ema_range.end == 'end':  # end is dict of {measure_num: num_of_beats}
                end = end[measure_num]
        else:
            end = score_info[unit].get(ema_range.end, ema_range.end)
        ema_list += [x for x in range(start, end + 1)]
    return ema_list
