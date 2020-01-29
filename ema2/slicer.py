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


# list of EmaRange -> list of int
def ema_to_list(ema_range_list, score_info, unit, measure_num=None):
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
    for m in range(len(measure_nums)):
        measure_num = measure_nums[m]
        measure_staves = ema_to_list(ema_exp.st_ranges[m], score_info, 'staff')
        for s in range(len(measure_staves)):
            stave_num = measure_staves[s]
            staff_beats = ema_to_list(ema_exp.bt_ranges[m][s], score_info, 'beat', measure_num)
            # Printout of all requested beats, with measure and stave matched up
            print(measure_num, stave_num, staff_beats)
            # new_score.append(score.measure(measure_num).parts[stave_num])
    # try:
    #     file_path = new_score.write('musicxml')
    # except Exception as e:
    #     return None
    # return file_path
