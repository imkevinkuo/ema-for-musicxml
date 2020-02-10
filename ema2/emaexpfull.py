from typing import List
from music21 import stream
import xml.etree.ElementTree as ET

from ema2.emaexp import EmaExp

""" Contains functions/imports that read score data in order to convert from EmaExpression to EmaExpressionFull."""


class EmaExpFull(object):
    """ Represents an EMA expression after evaluation of 'start/end' tokens and expansion of all ranges. """

    def __init__(self, score_info: dict, ema_exp: EmaExp):
        self.score_info = score_info
        self.selection = expand_ema_exp(score_info, ema_exp)  # list of EmaMeasure


class EmaStaff(object):
    def __init__(self, num: int, beats: List[int] = []):
        self.num = num
        self.beats = beats


class EmaMeasure(object):
    def __init__(self, num: int, staves: List[EmaStaff] = []):
        self.num = num
        self.staves = staves


def expand_ema_exp(score_info, ema_exp):
    """ Converts an EmaExpression to a List[EmaMeasure].
        :param score_info : Dict of {'measure/staff/beat': 'start'/'end': values}
        :param ema_exp    : An EmaExp representing the input string e.g. all/all/@all
    """
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


def ema_to_list(ema_range_list, score_info, unit, measure_num=None):
    """ Converts a list of EmaRanges to a list of ints.
        :param ema_range_list : List[EmaRange] describing a set of measures, staves, or beats.
        :param score_info     : Dict of {'measure/staff/beat': 'start'/'end': values}
        :param unit           : the type of range we are trying to evaluate ('measure'/'staff'/'beat')
        :param measure_num    : for unit='beat' only, measure number of this particular beat selection
        :return ema_list      : List[int] of all values specified in the EmaRanges
    """
    ema_list = []
    for ema_range in ema_range_list:
        start = score_info[unit].get(ema_range.start, ema_range.start)
        if unit == 'beat':
            end = score_info[unit].get(ema_range.end, ema_range.end)
            if ema_range.end == 'end':  # end is dict of {measure_num: num_of_beats}
                # Some measure ids might be strings?
                end = end[str(measure_num)]
        else:
            end = score_info[unit].get(ema_range.end, ema_range.end)
        ema_list += [x for x in range(start, end + 1)]
    return ema_list


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


def get_score_info_mxl(tree: ET.ElementTree):
    score_info = {'measure': {},
                  'staff': {
                      'start': 1
                  },
                  'beat': {
                      'start': 1
                      # 'end': {measure_num: num_of_beats}
                  }}
    parts = tree.getroot().findall('part')
    measures = parts[0].findall('measure')
    score_info['measure']['start'] = int(measures[0].attrib['number'])
    score_info['measure']['end'] = int(measures[-1].attrib['number'])
    score_info['staff']['end'] = len(parts)
    # have to traverse entire tree for this?
    # TODO: What happens when we have mxl files with non-integer measure numbers? e.g. '7a'
    score_info['beat']['end'] = {m.attrib['number']: 3 for m in measures}
    return score_info
