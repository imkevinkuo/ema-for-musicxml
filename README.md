# ema2
A MusicXML implementation of the [Enhancing Music Notation Addressability API](https://github.com/umd-mith/ema).

## Folder descriptions
ema2: Implementation for the EMA parser and MusicXML selector.

tst: Scrapes scores from the Digital Du Chemin nanopublication library and uses them to test ema2's correctness.

To download all the Digital Du Chemin scores, run `python scraper.py`.
Scraping one page may take up to 30 minutes; scraping all 11 pages of the database will take several hours.