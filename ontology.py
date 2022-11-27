import os
import json
from collections import defaultdict

import pandas as pd
from lxml import etree
from owlready2 import (
    get_ontology,
    Thing,
    ObjectProperty,
    FunctionalProperty,
    DataProperty
)

LANGS = {
    'rus': 'ru',
    'span': 'es'
}

CORPUS_FOLDER = os.path.join('corpus', 'final')
KWIC_FILENAME = os.path.join('intermediate_data_files', 'location_kwic.csv')
CORRECT_LINKS_FILENAME = os.path.join('disambiguation_annotation', 'correct_links.csv')
NORMALIZED_LOCATIONS_FILENAME = os.path.join(
    'intermediate_data_files',
    'locations_normalized.json'
)
CORPUS_INFO_FILENAME = 'corpus_ontology_info.json'

NAMESPACE = {
    'ns': 'http://www.tei-c.org/ns/1.0',
    'xml': 'http://www.w3.org/XML/1998/namespace'
}
UTTERANCE_XPATH = '//ns:sp'
LOC_XPATH = './/ns:loc'
TITLE_XPATH = '//ns:title[@type="main"]'
SPEAKER_XPATH = '//ns:particDesc/ns:listPerson/ns:person'

with open(NORMALIZED_LOCATIONS_FILENAME) as f:
    NORMALIZED_LOCATIONS = json.load(f)


onto = get_ontology("http://test.org/drama_locations")

with onto:
    class Language(Thing): pass
    class Play(Thing): pass
    class Speaker(Thing): pass
    class Location(Thing): pass
    class NMentions(Thing): pass

    class in_language(Play >> Language, ObjectProperty, FunctionalProperty): pass

    class has_characters(Play >> Speaker, ObjectProperty): pass

    class is_character_of(Speaker >> Play, ObjectProperty, FunctionalProperty):
        inverse_property = has_characters

    class mentions_n(Speaker >> NMentions, ObjectProperty): pass

    class is_about(NMentions >> Location, ObjectProperty, FunctionalProperty): pass

    class n(NMentions >> int, DataProperty, FunctionalProperty): pass

    class has_title(Play >> str, DataProperty, FunctionalProperty): pass

    class has_name(Speaker >> str, DataProperty, FunctionalProperty): pass

    class location_name(Location >> str, DataProperty): pass

    class wikidata_id(Location >> str, DataProperty): pass


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
        loc_norm = NORMALIZED_LOCATIONS[wikilang].get(loc, loc)
        links[wikilang][loc_norm] |= curr_links

    links = {
        lang: {loc: sorted(loc_links) for loc, loc_links in locs.items()}
        for lang, locs in links.items()
    }
    return links


def get_location_counts(tree, lang):
    location_counts = defaultdict(lambda: defaultdict(int))

    utterances = tree.xpath(UTTERANCE_XPATH, namespaces=NAMESPACE)
    for utterance in utterances:
        speaker = utterance.get('who').strip('#')
        locs = utterance.xpath(LOC_XPATH, namespaces=NAMESPACE)
        for loc in locs:
            loc_norm = NORMALIZED_LOCATIONS[LANGS[lang]].get(loc.text, loc.text)
            location_counts[speaker][loc_norm] += 1

    return location_counts


def get_play_title(tree):
    titles = tree.xpath(TITLE_XPATH, namespaces=NAMESPACE)
    for title in titles:
        lang = title.attrib.get(f'{{{NAMESPACE["xml"]}}}lang')
        if lang is None:
            return title.text


def get_play_speakers(tree):
    speakers = {}
    speaker_elems = tree.xpath(SPEAKER_XPATH, namespaces=NAMESPACE)
    for speaker_elem in speaker_elems:
        sp_id = speaker_elem.attrib.get(f'{{{NAMESPACE["xml"]}}}id')
        name = ''
        for child in speaker_elem:
            lang = child.attrib.get(f'{{{NAMESPACE["xml"]}}}lang')
            if child.tag == f"{{{NAMESPACE['ns']}}}persName" and lang is None:
                name = child.text
                break

        speakers[sp_id] = name

    return speakers


def get_play_info(playname, lang):
    with open(os.path.join(CORPUS_FOLDER, lang, playname)) as f:
        tree = etree.parse(f)

    location_counts = get_location_counts(tree, lang)
    title = get_play_title(tree)
    speakers = get_play_speakers(tree)

    return {
        'locations': location_counts,
        'title': title,
        'speakers': speakers
    }


def get_corpus_info():
    corpus_info = defaultdict(dict)

    for lang in LANGS:
        if lang.startswith('.'):
            continue

        playnames = os.listdir(os.path.join(CORPUS_FOLDER, lang))
        for playname in playnames:
            if not playname.endswith('.xml'):
                continue

            corpus_info[lang][playname] = get_play_info(playname, lang)

    return corpus_info


def create_speaker_obj(speaker_id, speaker_name, playname_obj):
    speaker_obj_id = f'#{playname_obj.name}_{speaker_id}'
    return Speaker(
        speaker_obj_id,
        has_name=speaker_name,
        is_character_of=playname_obj
    )


def create_speaker_objs(speaker_dict, playname_obj):
    speaker_obj_dict = {}
    for speaker_id, name in speaker_dict.items():
        speaker_obj_dict[speaker_id] = create_speaker_obj(
            speaker_id, name, playname_obj
        )
    return speaker_obj_dict


def get_loc_id(loc_links, loc_name):  # arbitrary decision
    return loc_links[0] if loc_links else f'NULL_{loc_name}'


def create_location_objs(links):
    location_data = defaultdict(lambda: defaultdict(set))
    for lang_links in links.values():
        for loc_name, loc_links in lang_links.items():
            loc_id = get_loc_id(loc_links, loc_name)
            location_data[loc_id]['links'] |= set(loc_links)
            location_data[loc_id]['names'].add(loc_name)

    locations = {}
    for loc_id, loc_data in location_data.items():
        loc = Location(loc_id)
        for link in loc_data['links']:
            loc.wikidata_id.append(link)
        for name in loc_data['names']:
            loc.location_name.append(name)
        locations[loc_id] = loc

    return locations


def add_play_to_ontology(playname, play_info, lang_obj, links, location_objs):
    playname_obj = Play(
        playname[:-4],
        in_language=lang_obj,
        has_title=play_info['title']
    )
    speakers = create_speaker_objs(play_info['speakers'], playname_obj)

    for speaker, places in play_info['locations'].items():
        speaker_obj = speakers.get(speaker)
        if speaker_obj is None:
            speaker_obj = create_speaker_obj(speaker, speaker, playname_obj)

        for place, n_mentions in places.items():
            place_links = links[LANGS[lang_obj.name]][place]
            location_id = get_loc_id(place_links, place)
            loc = location_objs[location_id]
            loc_mention_id = f'#mention_{speaker_obj.name}_{place}'
            mentions = NMentions(loc_mention_id, is_about=loc, n=n_mentions)
            speaker_obj.mentions_n.append(mentions)


def compile_ontology(corpus_info, links, location_objs):
    for lang, plays in corpus_info.items():
        lang_obj = Language(lang)

        for playname, info in plays.items():
            add_play_to_ontology(playname, info, lang_obj, links, location_objs)


if __name__ == '__main__':
    corpus_info = get_corpus_info()
    with open(CORPUS_INFO_FILENAME, 'w') as f:
        json.dump(corpus_info, f, indent=2, ensure_ascii=False)

    links = get_correct_links()
    location_objs = create_location_objs(links)
    compile_ontology(corpus_info, links, location_objs)
    onto.save('locations.owl')
