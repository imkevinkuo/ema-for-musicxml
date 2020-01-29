from flask import Flask, send_file
from ema2 import slicer, emaexpression
from music21 import converter, environment, stream
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
    """ Before constructing the EmaExpression, we determine some basic features of the score.
        e.g. first/last measure number, number of staves. """
    score: stream.Score = converter.parse(path)
    ema_exp = emaexpression.EmaExpression(measures, staves, beats, completeness)
    file_path = slicer.slice_score(score, ema_exp)
    return send_file(file_path)


if __name__ == "__main__":
    environment.set('autoDownload', 'allow')
    app.run(debug=True)
