import xml.etree.ElementTree as ET
from ema2 import emaexp, emaexpfull, slicer
path = "tests/bwv269.xml"
tree = ET.parse(path)
# expr = "0,2/all/@all"
expr = "1-3/3,1-3,1+4/@all,@all,@all"
ema_exp = emaexp.EmaExp(*expr.split("/"))
score_info = emaexpfull.get_score_info_mxl(tree)
ema_exp_full = emaexpfull.EmaExpFull(score_info, ema_exp)
resp = slicer.slice_score(tree, ema_exp_full)
resp.write('test.xml')
