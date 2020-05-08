from flask import Flask, send_file
from emaMXL import slicer
import xml.etree.ElementTree as ET

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return "Read the <a href=\"https://github.com/umd-mith/ema/blob/master/docs/api.md\">API specification</a>."


@app.route('/<path:path>/<measures>/<staves>/<beats>', methods=["GET"])
@app.route('/<path:path>/<measures>/<staves>/<beats>/<completeness>', methods=["GET"])
def address(path, measures, staves, beats, completeness=None):
    tree = slicer.slice_score_path(path, "/".join([measures, staves, beats, completeness if completeness else ""]))
    return app.response_class(ET.tostring(tree.getroot()), mimetype='application/xml')


if __name__ == "__main__":
    app.run(debug=True)
