import os
import re

import pandas as pd
from lxml import etree


NAMESPACE = {'ns': 'http://www.tei-c.org/ns/1.0'}
UTTERANCE_XPATH = '//ns:sp'
TEXT_XPATH = './ns:p'

P_REGEX = re.compile(r'<p.*?>(.+?)</p>')
LOC_REGEX = re.compile(r'(<loc(.*?)>(.+?)</loc>)')
SPACE_REGEX = re.compile(r'\s+')

CORPUS_FOLDER = os.path.join('corpus', 'final')
KWIC_FILENAME = 'location_kwic.csv'

LANGS = {
    'rus': 'ru',
    'span': 'es'
}


def process_utterance(lang, play, utterance, prev_utterance):
    """Compile kwic for one utterance."""
    curr_locs = []

    p_tags = utterance.xpath(TEXT_XPATH, namespaces=NAMESPACE)
    curr_utterance = ''
    for p in p_tags:
        xml_str = etree.tostring(p, encoding='utf-8').decode('utf-8')
        curr_utterance += ' ' + P_REGEX.sub(r'\1', xml_str)
    curr_utterance = SPACE_REGEX.sub(' ', curr_utterance)

    for loc in LOC_REGEX.finditer(curr_utterance):
        mode = 'fixed' if 'from="manual"' in loc.group(2) else 'auto'
        curr_locs.append([
            lang,
            play,
            mode,
            prev_utterance,
            curr_utterance[:loc.start()],
            loc.group(3),
            curr_utterance[loc.end():],
        ])

    return curr_utterance, curr_locs


def process_play(lang, folder, filename):
    """Compile kwic for one play."""
    with open(os.path.join(folder, filename)) as f:
        tree = etree.parse(f)

    play = filename[:-4]
    play_kwic = []

    prev_utterance = ''
    utterances = tree.xpath(UTTERANCE_XPATH, namespaces=NAMESPACE)

    for utterance in utterances:
        curr_utterance, utt_kwic = process_utterance(
            lang, play, utterance, prev_utterance
        )
        play_kwic += utt_kwic
        prev_utterance = curr_utterance

    return play_kwic


def get_kwic_df():
    """
    Compile kwic for all plays
    and write to KWIC_FILENAME file.
    """
    kwic = []

    for lang, wikilang in LANGS.items():
        folder = os.path.join(CORPUS_FOLDER, lang)
        for filename in os.listdir(folder):
            if filename.endswith('.xml'):
                kwic += process_play(lang, folder, filename)

    df = pd.DataFrame(
        kwic,
        columns=[
            'lang',
            'play',
            'extraction_mode',
            'prev_utterance',
            'utterance_left',
            'location',
            'utterance_right'
        ]
    )

    df.to_csv(
        KWIC_FILENAME,
        index=False,
        sep='\t'
    )


if __name__ == '__main__':
    get_kwic_df()
