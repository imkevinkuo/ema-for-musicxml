from music21 import stream
from ema2.emaexpression import EmaExpression


# dict:
#     measure: start: 0
#              end : 21
#              default: cast to int
def get_score_info(score: stream.Score):
    score_info = {'measure': {}, 'staff': {}, 'beat': {}}
    return score_info


# list of EmaRange, unit = 'measure'/'staff'/'beat' -> list of int
def ema_to_list(ema_range_list, score_info, unit):
    ema_list = []
    for ema_range in ema_range_list:
        start = score_info[unit].get(ema_range.start, lambda x: x)
        end = score_info[unit].get(ema_range.end, lambda x: x)
        ema_list += [x for x in range(start, end + 1)]
    return ema_list


def slice_score(score: stream.Score, ema_exp: EmaExpression):
    score_info = get_score_info(score)
    measure_nums = ema_to_list(ema_exp.mm_ranges, score_info, 'measure')
    new_score = stream.Score()
    for m in range(len(measure_nums)):
        measure_num = measure_nums[m]
        measure_staves = ema_to_list(ema_exp.st_ranges[m], 'staff')  # [EmaRange, EmaRange, ...] -> [1,2,4,5,6,8]
        measure_beats = ema_exp.bt_ranges[m]
        for s in range(len(measure_staves)):
            stave_num = measure_staves[s]
            staff_beats = ema_to_list(measure_beats[s], 'beat')
            print(staff_beats)
            # new_score.append(score.measure(measure_num).parts[stave_num])
    # try:
    #     file_path = new_score.write('musicxml')
    # except Exception as e:
    #     print("lol")
    #     return None
    # return file_path
