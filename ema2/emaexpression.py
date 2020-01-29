import itertools

from ema2.exceptions import BadApiRequest


class EmaExpression(object):
    """ A class to parse an EMA expression. Sub-objects are organized to reflect user input.
        We can't do any more simplifying than this without looking at the score.
    """
    def __init__(self, measures, staves, beats, completeness=None):
        # self.requested_measures = measures
        # self.requested_staves = staves
        # self.requested_beats = beats
        # self.completeness = completeness

        # list of EmaRange
        self.mm_ranges = parse_range_str_list(measures.split(','))
        # list of list of EmaRange
        self.st_ranges = [parse_range_str_list(stave_req_str.split("+")) for stave_req_str in staves.split(',')]
        # list of list of list of EmaRange
        self.bt_ranges = [[parse_range_str_list(stave_req_str.split("@")[1:])
                           for stave_req_str in measure_req_str.split("+")]
                          for measure_req_str in beats.split(',')]


class EmaRange(object):
    """ idk """
    def __init__(self, range_str):
        x = range_str.split("-")
        start, end = ema_token(x[0]), ema_token(x[-1])
        if start == 'end' and end != 'end':
            raise BadApiRequest
        if start == 'all' and end == 'all':
            start, end = 'start', 'end'
        self.start = start
        self.end = end


def parse_range_str_list(range_str_list, join=False):
    ema_range_list = []
    if join:
        last_end = -1
        for range_str in range_str_list:
            ema_range = EmaRange(range_str)
            if ema_range_list and ema_range.start == last_end + 1:
                ema_range_list[-1].end = ema_range.end
            else:
                ema_range_list.append(ema_range)
            last_end = ema_range.end
    else:
        for range_str in range_str_list:
            ema_range_list.append(EmaRange(range_str))
    return ema_range_list


def ema_token(token):
    if token == 'all' or token == 'start' or token == 'end':
        return token
    return int(token)


class EmaMeasure(object):
    """ hmm """
    def __init__(self, measure, st_range, bt_range):
        self.measure = measure
        self.selection = None
