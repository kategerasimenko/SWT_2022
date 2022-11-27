# Expanding drama ontology with geographical entities

Code for SWT course project at University of Groningen. <br>
Ekaterina Garanina, Lynne Zhang, Gaia Sasso

## Corpus and annotation

Corpus consists of drama texts in Russian and Spanish. Data is taken from open-source [DraCor project](https://dracor.org). All plays are in XML-TEI format.
* `corpus/autoparsed` - plays in XML with the locations automatically extracted with [Stanza](https://github.com/stanfordnlp/stanza).
* `corpus/fixed` - plays with the corrected locations, where manually annotated locations are enclosed in `{{ }}` brackets.
* `corpus/final` - final version of the corpus with unified annotation for furhter processing.

## How to run the code

### Requirements

* python 3.x
* pandas 1.1.x
* lxml 4.x
* stanza 1.4.x
* requests
* pymorphy2 (for location normalization in Russian) 0.9.1
* fairseq and GENRE (installation in GENRE.ipynb)
* owlready2 0.39


### Getting location mentions
* `NER.ipynb` - run NER on the corpus. After that, manual correction was conducted.
* `evaluate_ner.py` - run NER evaluation and compile a final corpus with correct annotations.
* `create_kwic.py` - create location list in KWIC format from the XML corpus.
* `create_location_list.py` - create a list of unique locations. For Russian, do automatic normalization (nominative case). Normalization requires manual correction.

### Entity linking
#### context-independent Wikidata linking
* `wikidata.py` - get candidates for each unique location, rank them with page scoring formula.
* `find_coefficients.py` - find the most optimal coefficients for ranking formula.

#### mGENRE
* `GENRE.ipynb` - run mGENRE model on XML corpus.

#### babelfy
* `create_plays_with_location_indices.py` - prepare input for babelfy inference and evaluation.
* `babelfy.ipynb` - run babelfy inference and evaluation. Personal API  key required.

### Posprocessing
* `create_location_hyperlinks.py` - create hyperlinked ranked candidate lists for each location in KWIC table. Required for manual evaluatiom.
* `ontology.py` - compile an OWL ontology containing plays, speakers, and locations.
* `graphs.ipynb` - provide examples of graphs about plays, speakers, and locations.
