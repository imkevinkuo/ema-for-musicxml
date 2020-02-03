from music21 import stream, converter
from ema2 import emaexpression, emaexpressionfull
path = "tests/omen_small.musicxml"
score: stream.Score = converter.parse(path)
# measures = "all"
# staves = "all"
# beats = "@all"
measures = "1-3,4,5-6"
staves = "1,2,3,1-3+5,2+3,4"
beats = "@all,@all,@all,@1-2@3+@all+@all+@all,@all+@all,@all"
completeness = None
ema_exp = emaexpression.EmaExpression(measures, staves, beats, completeness)
score_info = emaexpressionfull.get_score_info_m21(score)
ema_exp_full = emaexpressionfull.EmaExpressionFull(score_info, ema_exp)