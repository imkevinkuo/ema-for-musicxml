from ema2.exceptions import BadApiRequest

COMPLETENESS_VALUES = ['raw', 'signature', 'nospace', 'cut']


class EmaExp(object):
    """ Represents an EMA expression as inputted by a user; no expansion or evaluation of tokens are done yet.
        We cannot yet represent the request as a single nested structure because ranges including
        'start/end' contain an indeterminate number of measures/beats/staves.
        'all' is converted to 'start','end'.
    """
    def __init__(self, measures, staves=None, beats=None, completeness=None):
        # self.requested_measures = measures
        # self.requested_staves = staves
        # self.requested_beats = beats
        # self.completeness = completeness

        # Allows feeding in a single string as an argument
        if staves is None and beats is None:
            args = measures.split("/")
            if len(args) == 3:
                measures, staves, beats = args
            elif len(args) == 4:
                measures, staves, beats, completeness = args

        # list of EmaRange
        self.mm_ranges = parse_range_str_list(measures.split(','), 'measure')
        # list of list of EmaRange
        self.st_ranges = [parse_range_str_list(stave_req_str.split("+"), 'stave')
                          for stave_req_str in staves.split(',')]
        # list of list of list of EmaRange
        self.bt_ranges = [[parse_range_str_list(stave_req_str.split("@")[1:], 'beat')
                           for stave_req_str in measure_req_str.split("+")]
                          for measure_req_str in beats.split(',')]
        # Completeness
        if completeness not in COMPLETENESS_VALUES:
            completeness = None
        self.completeness = completeness

    @classmethod
    def fromstring(cls, selection):
        return cls(*selection.split("/"))


class EmaRange(object):
    """ Represents a (start, end) pair given in an EMA expression. """
    def __init__(self, range_str, unit):
        x = range_str.split("-")
        start, end = ema_token(x[0], unit), ema_token(x[-1], unit)
        if start == 'end' and end != 'end':
            raise BadApiRequest
        if end == 'start' and start != 'start':
            raise BadApiRequest
        if start == 'all' and end == 'all':
            start, end = 'start', 'end'
        self.start = start
        self.end = end

    def convert_to_time(self, factor):
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
        return EmaRange(f"{time_start}-{time_end}", "beat")

    def __str__(self):
        return f"[{self.start} {self.end}]"


def parse_range_str_list(range_str_list, unit, join=False):
    ema_range_list = []
    if join:
        last_end = -1
        for range_str in range_str_list:
            ema_range = EmaRange(range_str, unit)
            if ema_range_list and ema_range.start == last_end + 1:
                ema_range_list[-1].end = ema_range.end
            else:
                ema_range_list.append(ema_range)
            last_end = ema_range.end
    else:
        for range_str in range_str_list:
            ema_range_list.append(EmaRange(range_str, unit))
    return ema_range_list


def ema_token(token, unit):
    if token == 'all' or token == 'start' or token == 'end':
        return token
    if unit == 'beat':
        return float(token)
    return int(token)
