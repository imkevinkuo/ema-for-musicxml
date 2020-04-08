from flask import Flask, send_file
from ema2 import slicer
from ema2.emaexp import EmaExp
from ema2.emaexpfull import EmaExpFull, get_score_info_mxl
import xml.etree.ElementTree as ET

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return "Welcome to EMA"


@app.route(
    '/<path:path>/<measures>/<staves>/<beats>',
    methods=["GET"])
@app.route(
    '/<path:path>/<measures>/<staves>/<beats>/<completeness>',
    methods=["GET"])
def address(path, measures, staves, beats, completeness=None):
    score = ET.parse(path)
    ema_exp = EmaExpFull(get_score_info_mxl(score), EmaExp(measures, staves, beats, completeness))
    file_path = slicer.slice_score(score, ema_exp)
    return send_file(file_path)


if __name__ == "__main__":
    app.run(debug=True)
