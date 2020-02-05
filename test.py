import xml.etree.ElementTree as ET
from ema2 import emaexpression, emaexpressionfull, slicer
path = "tests/bwv269.xml"
tree = ET.parse(path)
measures = "start-1"
staves = "all"
beats = "@all"
# measures = "1-3,4,5-6"
# staves = "1,2,3,1-4,2+3,3"
# beats = "@all,@all,@all,@1-2@3+@all+@all+@all,@all+@all,@all"
completeness = None
ema_exp = emaexpression.EmaExpression(measures, staves, beats, completeness)
score_info = emaexpressionfull.get_score_info_mxl(tree)
ema_exp_full = emaexpressionfull.EmaExpressionFull(score_info, ema_exp)
resp = slicer.slice_score(tree, ema_exp_full)
resp.write('test.xml')
