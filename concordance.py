import os
import re

import pandas as pd
from lxml import etree


NAMESPACE = {'ns': 'http://www.tei-c.org/ns/1.0'}
UTTERANCE_XPATH = '//ns:sp'
TEXT_XPATH = './ns:p'

P_REGEX = re.compile(r'<p.*?>(.+?)</p>')
LOC_REGEX = re.compile(r'(<loc>(.+?)</loc>)')
SPACE_REGEX = re.compile(r'\s+')

CORPUS_FOLDER = os.path.join('corpus', 'final')
LANGS = ['rus', 'span']

concordance = []

for lang in LANGS:
    folder = os.path.join(CORPUS_FOLDER, lang)
    for filename in os.listdir(folder):
        if not filename.endswith('.xml'):
            continue

        play = filename[:-4]
        with open(os.path.join(folder, filename)) as f:
            tree = etree.parse(f)

        prev_utterance = ''
        utterances = tree.xpath(UTTERANCE_XPATH, namespaces=NAMESPACE)
        for utterance in utterances:
            curr_utterance = ''
            p_tags = utterance.xpath(TEXT_XPATH, namespaces=NAMESPACE)
            for p in p_tags:
                xml_str = etree.tostring(p, encoding='utf-8').decode('utf-8')
                curr_utterance += ' ' + P_REGEX.sub('\\1', xml_str)
            curr_utterance = SPACE_REGEX.sub(' ', curr_utterance)
            for loc in LOC_REGEX.finditer(curr_utterance):
                concordance.append([
                    lang,
                    play,
                    prev_utterance,
                    curr_utterance[:loc.start()],
                    loc.group(2),
                    curr_utterance[loc.end():]
                ])
            prev_utterance = curr_utterance


df = pd.DataFrame(
    concordance,
    columns=['lang', 'play', 'prev_utterance', 'utterance_left', 'location', 'utterance_right']
)
df.to_csv(
    'location_concordance.csv',
    index=False
)
