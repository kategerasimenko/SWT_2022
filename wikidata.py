import re
import json
import requests
from time import sleep
from math import log
from collections import defaultdict


NORM_LOC_FILENAME = 'locations_normalized.json'
LOC_INFO_FILENAME = 'wikidata_locations_info.json'
RANKING_FILENAME = 'wikidata_ranking.json'
COEFS_FILENAME = 'coefficients.json'

EMAIL = 'e.garanina@student.rug.nl'
SPARQL_URL = 'https://query.wikidata.org/sparql'  # for SPARQL queries
ENTITY_URL = 'https://www.wikidata.org/wiki/Special:EntityData/%s.json'  # for retrieving entities by ID
USER_AGENT = {'User-Agent': f'Location extractor ({EMAIL})'}  # to avoid ban


# limit entities to subclasses of
# wd:Q82794 - `geographic region` and
# wd:Q2221906 - `geographic location.

# Heavy query:
# use fulltext search (for speed) to search by label and aliases;
# limit search and output to relevant language;
# output id, primary label, and all aliases.

GEO_REGION = 'Q82794'
GEO_LOC = 'Q2221906'

HEAVY_CANDIDATE_QUERY = """
SELECT DISTINCT ?locId ?label ?altLabel WHERE {
  ?loc wdt:P31/wdt:P279* wd:%s .
  SERVICE wikibase:mwapi {
    bd:serviceParam wikibase:endpoint "www.wikidata.org";
                    wikibase:api "Generator";
                    mwapi:generator "search";
                    mwapi:gsrsearch 'inlabel:"%s@%s"';
                    mwapi:gsrlimit "max".
    ?loc wikibase:apiOutputItem mwapi:title.
  }
  SERVICE wikibase:label { 
    bd:serviceParam wikibase:language "%s". 
    ?loc rdfs:label ?label;
         skos:altLabel ?altLabel.
  }
  BIND(STRAFTER(STR(?loc), STR(wd:) ) as ?locId)
}
"""


# light query:
# exact match with primary label;
# output id and primary label.

LIGHT_CANDIDATE_QUERY = """
SELECT DISTINCT ?locId ?label WHERE {
  ?loc wdt:P31/wdt:P279* wd:%s;
       rdfs:label "%s"@%s.
  SERVICE wikibase:label { 
    bd:serviceParam wikibase:language "%s". 
    ?loc rdfs:label ?label.
  }
  BIND(STRAFTER(STR(?loc), STR(wd:) ) as ?locId)
}
"""


# query to get links TO the page

LINKS_QUERY = """
SELECT DISTINCT (COUNT(?entity) AS ?entityCount) WHERE {
  ?entity ?property wd:%s .
  ?prop wikibase:directClaim ?property .
}
"""


def create_loc_regexes(loc):
    """
    Create regexes for general and bracketed locations.
    """
    loc_regex = re.compile(rf'{loc}', flags=re.I)
    loc_regex_brackets = re.compile(rf'\([^)]*?{loc}[^(]*?\)', flags=re.I)
    return loc_regex, loc_regex_brackets


def get_candidates(ancestor_id, loc_name, lang, loc_regex, loc_regex_brackets):
    """
    Query Wikidata by location name and language.
    Filter and reformat results.
    """
    heavy_query = HEAVY_CANDIDATE_QUERY % (ancestor_id, loc_name, lang, lang)
    light_query = LIGHT_CANDIDATE_QUERY % (ancestor_id, loc_name, lang, lang)

    try:
        r = requests.get(
            SPARQL_URL,
            params={'format': 'json', 'query': heavy_query},
            headers=USER_AGENT,
            timeout=60
        )

    # If heavy query timeouts (too many objects to retrieve),
    # the entity is large and famous (e.g. capital or country),
    # so run lighter exact match query.
    except requests.exceptions.Timeout:
        print(f'Heavy query timeout: {loc_name}, {lang}. Trying exact query')
        r = requests.get(
            SPARQL_URL,
            params={'format': 'json', 'query': light_query},
            headers=USER_AGENT
        )

    candidates = r.json()['results']['bindings']
    candidates = [
        c['locId']['value'] for c in candidates
        if not is_bracketed(c, loc_regex, loc_regex_brackets)
    ]

    return candidates


def is_bracketed(data, loc_regex, loc_regex_brackets):
    """
    Check if the location is always mentioned in brackets
    in all locations.
    """
    all_labels = f"{data['label']['value']} {data.get('altLabel', {}).get('value', '')}"
    n_locs = len(loc_regex.findall(all_labels))
    n_locs_brackets = len(loc_regex_brackets.findall(all_labels))
    return n_locs == n_locs_brackets


def get_entity(entity_id):
    """
    Retrieve Wikidata entity by id.
    """
    data = requests.get(
        ENTITY_URL % entity_id,
        headers=USER_AGENT
    ).json()['entities'][entity_id]
    return data


def get_n_links(entity_id):
    """
    Get number of links TO the entity.
    """
    l_query = LINKS_QUERY % entity_id
    l_r = requests.get(
        SPARQL_URL,
        params={'format': 'json', 'query': l_query},
        headers=USER_AGENT
    ).json()
    n_links = int(l_r['results']['bindings'][0]['entityCount']['value'])
    return n_links


def get_entity_info(lang, data, entity_id):
    """
    Get all numbers characterizing entity "importance" and
    and other details for later processing from full entity data.
    """
    info = {
        'n_labels': len(data['labels']),
        'n_descriptions': len(data['descriptions']),
        'n_sitelinks': len(data['sitelinks']),
        'n_aliases': sum(len(a) for a in data['aliases'].values()),
        'n_statements': sum(len(s) for s in data['claims'].values()),
        'n_qualifiers': sum(
            len(claim.get('qualifiers', []))
            for claims in data['claims'].values()
            for claim in claims
        ),
        'n_references': sum(
            len(claim.get('references', []))
            for claims in data['claims'].values()
            for claim in claims
        ),
        'n_links': get_n_links(entity_id),
        'label': data['labels'].get(lang, {}).get('value'),
        'aliases': [x['value'] for x in data['aliases'].get(lang, [])],
        'wikipedia_url': data['sitelinks'].get(f'{lang}wiki', {}).get('url')
    }

    return info


def collect_candidates(unique_locations):
    location_candidates = defaultdict(dict)
    unique_candidates = defaultdict(set)

    for lang, locs in unique_locations.items():
        print(f'Getting candidates for {lang}: {len(locs)} unique locations')
        for i, loc in enumerate(locs):
            print(loc)
            if not i % 50:
                sleep(2)

            loc_regex, loc_regex_brackets = create_loc_regexes(loc)

            candidates = get_candidates(GEO_REGION, loc, lang, loc_regex, loc_regex_brackets)
            if not candidates:
                candidates = get_candidates(GEO_LOC, loc, lang, loc_regex, loc_regex_brackets)

            location_candidates[lang][loc] = candidates
            unique_candidates[lang] |= set(candidates)

    return location_candidates, unique_candidates


def get_candidates_stats(unique_candidates):
    entities_data = defaultdict(dict)
    for lang, entity_set in unique_candidates.items():
        print(f'Getting stats for {lang}: {len(entity_set)} unique entities')
        for i, entity_id in enumerate(entity_set):
            if not i % 50:
                sleep(2)

            entity = get_entity(entity_id)
            if entity is None:
                continue

            info = get_entity_info(lang, entity, entity_id)
            if info['wikipedia_url'] is None:
                continue

            entities_data[lang][entity_id] = info

    return entities_data


def calculate_score(query, entity_info, coefs):
    """
    Calculate score based on entity stats
    and optimal coefficients.
    """
    if query == entity_info['label']:
        coef = coefs['label']
    elif query in entity_info['aliases']:
        coef = coefs['aliases']
    else:
        coef = 1

    stat_sum = 0
    for key, value in coefs.items():
        if key in ['label', 'aliases']:
            continue

        stat = entity_info[key]
        stat = log(stat + 1) if value == 'log' else stat * value
        stat_sum += stat

    score = coef * stat_sum
    return round(score, 3)


def score_candidates(location_candidates, candidates_stats, coefs):
    scores = defaultdict(dict)
    for lang, locs in location_candidates.items():
        for loc, candidates in locs.items():
            loc_scores = []

            for candidate_id in candidates:
                candidate_info = candidates_stats[lang].get(candidate_id)
                if candidate_info is None:
                    continue

                score = calculate_score(loc, candidate_info, coefs)
                loc_scores.append([
                    candidate_id,
                    score,
                    candidate_info['wikipedia_url']
                ])

            scores[lang][loc] = sorted(loc_scores, key=lambda x: x[1], reverse=True)

    return scores


def get_stats():
    with open(NORM_LOC_FILENAME) as f:
        unique_locations = {
            lang: set(locs.values())
            for lang, locs in json.load(f).items()
        }

    location_candidates, unique_candidates = collect_candidates(unique_locations)
    candidates_stats = get_candidates_stats(unique_candidates)

    with open(LOC_INFO_FILENAME, 'w') as f:
        json.dump(
            {
                'candidates': location_candidates,
                'stats': candidates_stats
            },
            f,
            ensure_ascii=False
        )


def get_ranking():
    with open(LOC_INFO_FILENAME) as f:
        info = json.load(f)

    with open(COEFS_FILENAME) as f:
        coefs = json.load(f)

    scores = score_candidates(info['candidates'], info['stats'], coefs)

    with open(RANKING_FILENAME, 'w') as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

    return scores


if __name__ == '__main__':
    get_stats()
    get_ranking()
