import re
import os
import json
from collections import defaultdict

import pandas as pd
from lxml import etree


NAMESPACE = {'ns': 'http://www.tei-c.org/ns/1.0'}
UTTERANCE_XPATH = '//ns:sp'
TEXT_XPATH = './ns:p'
LOC_XPATH = './/ns:loc'

SPACE_REGEX = re.compile(r'\s+')
LOC_REGEX = re.compile(r'\[START\] (.+?) \[END\]')

LANGS = {
    'rus': 'ru',
    'span': 'es'
}

DATA_DIR = 'intermediate_data_files'
ANN_DIR = 'disambiguation_annotation'
KWIC_FILENAME = os.path.join(DATA_DIR, 'location_kwic.csv')
CORRECT_LINKS_FILENAME = os.path.join(ANN_DIR, 'correct_links.csv')
LOCATION_IDXS_FILENAME = os.path.join(DATA_DIR, 'plays_with_location_indices.json')


def get_correct_links():
    kwic = pd.read_csv(KWIC_FILENAME, sep='\t')
    locations = list(kwic.location)
    langs = list(kwic.lang)

    with open(CORRECT_LINKS_FILENAME) as f:
        raw_links = f.read().split('\n')

    assert len(raw_links) == len(locations)

    links = defaultdict(lambda: defaultdict(set))
    for lang, loc, raw_link in zip(langs, locations, raw_links):
        wikilang = LANGS[lang]
        raw_link = raw_link.strip().strip(',')
        curr_links = raw_link.split(',') if raw_link else []
        curr_links = set(curr_links)
        links[wikilang][loc] |= curr_links

    return links


def get_text_parts(p_tag):
    """
    In <p> tag, separate raw text and XML elements.
    Treat `note` tags as nested <p>.
    if `text_only_for_loc` is True, write only raw text for loc tags.
    """
    parts = [' ']

    if p_tag.text:
        parts.append(p_tag.text)

    for child in p_tag:
        if child.tag == f'{{{NAMESPACE["ns"]}}}note':
            parts += get_text_parts(child)
            continue

        parts.append(child)

        if child.tail:
            parts.append(child.tail)

    return parts


def compile_relevant_texts(parts):
    """
    From all parts of <p> tag (got from get_text_parts),
    compile text with annotated locations.
    """
    selected_parts = []
    for part in parts:
        text = part if isinstance(part, str) else part.text

        if not isinstance(part, str):
            # leave out <stage> tag
            if part.tag == f'{{{NAMESPACE["ns"]}}}stage':
                continue

            # save parts that contain target locations
            elif part.tag == f'{{{NAMESPACE["ns"]}}}loc':
                text = f'[START] {text} [END]'

        selected_parts.append(text)

    return SPACE_REGEX.sub(' ', ''.join(selected_parts)).strip()


def get_location_text_for_utterance(p_tags):
    """
    Parse locations in all <p> tags inside one speaker's utterance
    and create a text with annotated locations.
    """
    # one flat list of parts for the whole utterance (multiple <p> tags)
    all_parts = [part for p_tag in p_tags for part in get_text_parts(p_tag)]
    utterance_loc_text = compile_relevant_texts(all_parts)
    return utterance_loc_text


def get_location_texts_for_play(tree):
    """
    Given XML of a play, find all utterances with locations,
    and create a text with annotated locations for each utterance.
    """
    linking_texts = []

    utterances = tree.xpath(UTTERANCE_XPATH, namespaces=NAMESPACE)
    print('N utterances', len(utterances))

    for utterance in utterances:
        p_tags = utterance.xpath(TEXT_XPATH, namespaces=NAMESPACE)
        linking_texts.append(get_location_text_for_utterance(p_tags))
    return linking_texts


def get_indices_for_locations(text, links):
    """
    Given a text with annotated locations,
    calculate indices of locations in the raw text
    and remove all annotation tokens.
    Include correct wikidata link for each location.
    """
    new_text = ''
    end_idx = 0
    offset = 0
    loc_idxs = []

    locs = LOC_REGEX.finditer(text)
    for loc in locs:
        text_piece = text[end_idx:loc.start()]
        new_text += text_piece
        offset += len(text_piece)
        loc_st = offset

        loc_name = loc.group(1)
        new_text += loc_name
        offset += len(loc_name)
        loc_end = offset

        if links[loc_name]:
            link = ', '.join([
                f'https://www.wikidata.org/wiki/{l}'
                for l in links[loc_name]
            ])
        else:
            link = ''
        loc_idxs.append([loc_name, [loc_st, loc_end], link])
        end_idx = loc.end()

    new_text += text[end_idx:]

    return [new_text, loc_idxs]


def process_play(xml_path, links):
  """
  The main function.
  Get texts with annotated locations for each utterance in the play,
  get indices of locations in the text.
  """
  with open(xml_path) as f:
    tree = etree.parse(f)

  linking_texts = get_location_texts_for_play(tree)
  linking_text = '\n'.join(linking_texts)
  text_with_indices = get_indices_for_locations(linking_text, links)

  return text_with_indices


if __name__ == '__main__':
    langs = os.listdir(os.path.join('corpus', 'final'))
    locations = defaultdict(dict)

    links = get_correct_links()

    for lang in langs:
        if lang.startswith('.'):
            continue

        corpus_dir = os.path.join('corpus', 'final', lang)
        for playname in os.listdir(corpus_dir):
            if not playname.endswith('.xml'):
                continue

            print(playname)
            xml_path = os.path.join(corpus_dir, playname)
            play_locations = process_play(xml_path, links[LANGS[lang]])
            locations[lang][playname[:-4]] = play_locations

    with open(LOCATION_IDXS_FILENAME, 'w') as f:
        json.dump(locations, f, ensure_ascii=False)
