from xml.dom import minidom
from ema2.emaexpressionfull import EmaExpressionFull


# partwise - also only works on .musicxml, not .mxl (compressed format)
def slice_score(score: minidom.Document, ema_exp: EmaExpressionFull):
    for ema_measure in ema_exp.selection:
        measure_num = ema_measure.measure
        for ema_staff in ema_measure.staves:
            staff_num = ema_staff.staff
            beats = ema_staff.beats
            # TODO slice stuff
    return None
