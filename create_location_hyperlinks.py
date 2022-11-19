import json
from collections import Counter

import pandas as pd

from create_kwic import KWIC_FILENAME


TOP_LINKS = 5
GENRE_THRESHOLD = -0.65

WIKIDATA_LINKS_FILENAME = 'wikidata_ranking.json'
NORMALIZED_LOCATIONS_FILENAME = 'locations_normalized.json'
GENRE_LINKS_FILENAME = 'genre_ranking.json'

FINAL_LINKS_FILENAME = '%s_location_links.csv'
HEADER = [f'link{i+1}' for i in range(TOP_LINKS)]

LANGS = {
    'rus': 'ru',
    'span': 'es'
}


def hyperlink_str(score_tuple):
    """Create a hyperlink formula for Google Sheets."""
    id_, _, link = score_tuple
    return f'=HYPERLINK("{link}";"{id_}")'


def get_wikidata_links_for_kwic(df):
    """
    Create columns with wikidata (context-independent) linking
    corresponding to locations in existing kwic representation;
    write columns to a separate csv.
    """
    with open(WIKIDATA_LINKS_FILENAME) as f:
        location_scores = json.load(f)

    with open(NORMALIZED_LOCATIONS_FILENAME) as f:
        normalized_locations = json.load(f)

    links = []

    for _, row in df.iterrows():
        lang = LANGS[row['lang']]
        normalized_loc = normalized_locations[lang][row['location']]
        loc_scores = location_scores[lang][normalized_loc]
        hyperlinks = [hyperlink_str(s) for s in loc_scores[:TOP_LINKS]]
        links.append(hyperlinks)

    links_df = pd.DataFrame(links, columns=HEADER)
    links_df.to_csv(FINAL_LINKS_FILENAME % 'wikidata', index=False, sep='\t')


def get_genre_links_for_kwic(df):
    """
    Create columns with GENRE linking corresponding to
    locations in existing kwic representation;
    write columns to a separate csv.
    """
    with open(GENRE_LINKS_FILENAME) as f:
        location_scores = json.load(f)

    # check if kwic and linking data match.
    locs_by_play = dict(Counter(df.play))
    links_by_play = {
        play: len(locs)
        for play, locs in location_scores.items()
    }
    assert locs_by_play == links_by_play

    links = []

    plays = df.groupby('play', sort=False)
    for play_name, play_locs in plays:
        for i in range(play_locs.shape[0]):
            loc_scores = location_scores[play_name][i]['scores']
            hyperlinks = [hyperlink_str(s) for s in loc_scores[:TOP_LINKS]]
            links.append(hyperlinks)

    links_df = pd.DataFrame(links, columns=HEADER)
    links_df.to_csv(FINAL_LINKS_FILENAME % 'genre', index=False, sep='\t')


if __name__ == '__main__':
    df = pd.read_csv(KWIC_FILENAME, sep='\t')
    get_wikidata_links_for_kwic(df)
    get_genre_links_for_kwic(df)
