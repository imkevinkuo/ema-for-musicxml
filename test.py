import ema2.slicer as slicer
path = "tests/omen_small.mxl"
from music21 import stream, converter
from ema2 import emaexpression
score: stream.Score = converter.parse(path)
measures = "all"
# measures = "1-3,4,5-6"
staves = "all"
# staves = "1,2,3,1-3+5,2+3,4"
beats = "@all"
# beats = "@all,@all,@all,@1-2@3+@all+@all+@all,@all+@all,@all"
completeness = None
ema_exp = emaexpression.EmaExpression(measures, staves, beats, completeness)
new_score = slicer.slice_score(score, ema_exp)