# Expanding drama ontology with geographical entities

Code for SWT course project at University of Groningen. <br>
Ekaterina Garanina, Lynne Zhang, Gaia Sasso

## Corpus and annotation

TODO

## How to run the code

* python 3.x
* todo: requirements.txt

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
TODO

### Posprocessing
* `create_location_hyperlinks.py` - create hyperlinked ranked candidate lists for each location in KWIC table. Required for manual evaluatiom.
* `ontology.py` - compile an OWL ontology containing plays, speakers, and locations. Provide examples of SPARQL queries. 
* `graphs.ipynb` - provide examples of graphs about plays, speakers, and locations.