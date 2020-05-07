# ema-for-musicxml
A MusicXML implementation of the [Enhancing Music Notation Addressability API](https://github.com/umd-mith/ema).

## Description and Usage

### api.py
Flask server for using EMA as a web API.

Using the API through Python:
```
import requests
requests.get("http://localhost:5000/<musicxml_file_url>/<measures>/<staves>/<beats>/<completeness>")
```

By web browser: type `http://localhost:5000/<musicxml_file_url>/<measures>/<staves>/<beats>/<completeness>` into the address bar.

By terminal: `curl http://localhost:5000/<musicxml_file_url>/<measures>/<staves>/<beats>/<completeness>`

### emaMXL
Implementation for the EMA parser and MusicXML selector.

Programmatic usage in a Python console:
```
import ema2.slicer as slicer
slicer.slice_score_path(filepath, exp_str)
``` 

### tst
Scrapes scores from the Digital Du Chemin nanopublication library, converts them from MEI to MusicXML and uses them to test ema2's correctness.Note that some nanopublications are inaccurate or will be converted incorrectly by Music21.

To download all the Digital Du Chemin scores, run `python scraper.py`.
Scraping one page may take up to 30 minutes; scraping all 11 pages of the database will take several hours.
