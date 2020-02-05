import xml.etree.ElementTree as ET
from ema2.emaexpressionfull import EmaExpressionFull


# partwise - also only works on .musicxml, not .mxl (compressed format)
# to support duplicate requests like 2,2/@all/@all, we use an adding-based approach
def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpressionFull):
    score = tree.getroot()
    old_parts, new_parts = [], []
    for child in score:
        if child.tag == 'part':
            old_parts.append(child)
            new_parts.append(copy_xml_node_attr(child))
    current_measure = 0
    for ema_measure in ema_exp_full.selection:
        measure_num = ema_measure.num
        # When copying first measure, identify if it is a pickup measure.
        if current_measure == 0 and measure_num == 1:
            current_measure = 1
        req_staves = {staff.num: staff for staff in ema_measure.staves}
        # loop over all stave numbers (not just requested ones)
        for staff_num in range(len(new_parts)):
            old_measure = old_parts[staff_num][measure_num]
            new_measure = copy_xml_node_attr(old_measure)
            new_measure.attrib['number'] = str(current_measure)
            # TODO: find unit duration, calculate beats
            # need to append rests
            if staff_num in req_staves:
                beats = req_staves[staff_num].beats
                # new_measure = append_beats(new_measure, beats, old_measure)
            new_measure = append_beats(new_measure, None, old_measure)
            #
            new_parts[staff_num].append(new_measure)
            print(current_measure, staff_num)
        current_measure += 1
    for part in score.findall('part'):
        score.remove(part)
    for new_part in new_parts:
        score.append(new_part)
    # tree is already updated
    return tree


def append_beats(new_measure, beats, old_measure):
    for x in old_measure:
        # if x.tag == 'note' or x.tag == 'rest':
        new_measure.append(x)
    return new_measure


def copy_xml_node_attr(old_node):
    new_node = ET.Element(old_node.tag, old_node.attrib)
    new_node.text = old_node.text
    new_node.tail = old_node.tail
    return new_node
