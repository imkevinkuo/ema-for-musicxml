path = "tests/omen.mxl"
from music21 import stream, converter
from ema2 import emaexpression
score: stream.Score = converter.parse(path)
measures = "1-3,4,5-6"
staves = "1,2,3,1-3+5,2+3,4"
beats = "@all"
beats = "@all,@all,@all,@1-2@3+@all+@all+@all,@all+@all,@all"
completeness = None
ema_exp = emaexpression.EmaExpression(measures, staves, beats, completeness)
from ema2.slicer import get_score_info, ema_to_list
score_info = get_score_info(score)
measure_nums = ema_to_list(ema_exp.mm_ranges, score_info, 'measure')