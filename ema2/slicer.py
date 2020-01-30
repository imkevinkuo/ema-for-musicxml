from music21 import stream
from ema2.emaexpression import EmaExpression


def get_score_info(score: stream.Score):
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


def slice_score(score: stream.Score, ema_exp: EmaExpression):
    score_info = get_score_info(score)
    measure_nums = ema_to_list(ema_exp.mm_ranges, score_info, 'measure')
    new_score = stream.Score()
    # music21 streams are organized by Score > Part > Measure
    # Create empty parts inside the new score, copy other objects
    for item in score:
        if type(item) == stream.Part:
            new_part = stream.Part()
            new_part.partName = item.partName
            new_part.partAbbreviation = item.partAbbreviation
            new_part.id = item.id
            for part_item in item:
                if type(part_item) != stream.Measure:
                    new_part.append(part_item)
            new_score.append(new_part)
        else:
            new_score.append(item)
    for m in range(len(measure_nums)):
        measure_num = measure_nums[m]

        # this is hacky ill fix later
        m2 = m
        if len(ema_exp.st_ranges) == 1:
            m2 = 0
        measure_staves = ema_to_list(ema_exp.st_ranges[m2], score_info, 'staff')

        # Create blank measure if part was not selected for this measure
        for s in range(score_info['staff']['end']):
            if s+1 not in measure_staves:
                new_score.parts[s].append(stream.Measure(measure_num))
        # Insert beats for parts that were requested
        for s in range(len(measure_staves)):
            stave_num = measure_staves[s]
            print(m, s)
            # this is hacky too ill fix later
            s2 = s
            if len(ema_exp.bt_ranges) == 1:
                s2 = 0
            staff_beats = ema_to_list(ema_exp.bt_ranges[m2][s2], score_info, 'beat', measure_num)

            # Printout of all requested beats, with measure and stave matched up
            # print(measure_num, stave_num, m, s, staff_beats)
            # this is gonna be complicated, maybe have to iterate from time 0 up to end
            # for b in staff_beats:
            # gonna have to make a function to get X note at Y time step
            new_measure = stream.Measure(measure_num)
            notes = score.parts[stave_num - 1].measure(measure_num).notesAndRests
            for note in notes:
                new_measure.append(note)
            new_score.parts[stave_num - 1].append(new_measure)
    return new_score
    # try:
    #     file_path = new_score.write('musicxml')
    # except Exception as e:
    #     return None
    # return file_path
