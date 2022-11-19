import json
from collections import defaultdict

import pandas as pd
from pymorphy2 import MorphAnalyzer

from create_kwic import KWIC_FILENAME


# Create a list of locations with their normalized versions.
# Resulting file must be manually corrected for Russian (normalization errors).

m = MorphAnalyzer()

LANG_MAPPING = {
    'rus': 'ru',
    'span': 'es'
}


def capitalize(nomn_token, token):
    """
    Repeat capitalization of the original name.
    """
    tok_spl = token.split('-')
    nomn_tok_spl = nomn_token.split('-')
    assert len(tok_spl) == len(nomn_tok_spl)

    nomn_tok_spl = [
        np.capitalize() if p[0].isupper() else np
        for np, p in zip(nomn_tok_spl, tok_spl)
    ]
    return '-'.join(nomn_tok_spl)


def location_to_nomn(loc):
    """
    For Russian: inflect location name to nominative case.
    """
    tokens = loc.strip().split()
    nomn_tokens = []

    for token in tokens:
        all_parsed = m.parse(token)
        parsed = all_parsed[0]
        for item in all_parsed[1:]:
            if 'Geox' in item.tag:
                parsed = item
                break

        nomn_token = parsed.inflect({'nomn'}).word
        nomn_token = capitalize(nomn_token, token)
        nomn_tokens.append(nomn_token)

    return ' '.join(nomn_tokens)


if __name__ == '__main__':
    all_locs = pd.read_csv(KWIC_FILENAME)
    norm_locs = defaultdict(dict)

    for lang in ['rus', 'span']:
        locs = all_locs.loc[all_locs.lang == lang, 'location'].to_list()
        for loc in locs:
            norm_loc = location_to_nomn(loc) if lang == 'rus' else loc
            norm_locs[LANG_MAPPING[lang]][loc] = norm_loc

    with open('locations_normalized.json', 'w') as f:
        json.dump(norm_locs, f, ensure_ascii=False, indent=2)
