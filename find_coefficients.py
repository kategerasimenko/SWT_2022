import json
import random
from collections import defaultdict

import pandas as pd

from create_kwic import KWIC_FILENAME
from wikidata import score_candidates


random.seed(42)

LANGS = {
    'rus': 'ru',
    'span': 'es'
}

NORMALIZED_LOCATIONS_FILENAME = 'locations_normalized.json'
LOC_INFO_FILENAME = 'wikidata_locations_info.json'
COEFS_FILENAME = 'coefficients.json'

COEFS_GRID = [
    ['n_labels', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['n_descriptions', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['n_sitelinks', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['n_aliases', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['n_statements', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['n_qualifiers', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['n_references', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['n_links', [0, 0.25, 0.5, 1, 2, 4, 'log']],
    ['label', [1, 1.25, 1.5, 2, 3, 4]],
    ['aliases', [1, 1.25, 1.5, 2, 3, 4]]
]

DEFAULT = {k[0]: 1 for k in COEFS_GRID}
DEFAULT['n_links'] = 'log'


def get_correct_links():
    kwic = pd.read_csv(KWIC_FILENAME, sep='\t')
    locations = list(kwic.location)
    langs = list(kwic.lang)

    with open(NORMALIZED_LOCATIONS_FILENAME) as f:
        normalized_locations = json.load(f)

    with open('correct_links.csv') as f:
        raw_links = f.read().split('\n')

    assert len(raw_links) == len(locations)

    links = defaultdict(lambda: defaultdict(set))
    for lang, loc, raw_link in zip(langs, locations, raw_links):
        wikilang = LANGS[lang]
        raw_link = raw_link.strip().strip(',')
        curr_links = raw_link.split(',') if raw_link else []
        curr_links = set(curr_links)
        loc_norm = normalized_locations[wikilang].get(loc, loc)
        links[wikilang][loc_norm] |= curr_links

    return links


def dev_test_split(links):
    dev_locs = {}
    test_locs = {}

    for lang, lang_locs in links.items():
        lang_locs = sorted(lang_locs.keys())
        n_dev = len(lang_locs) // 2
        lang_dev_locs = set(random.sample(lang_locs, n_dev))
        dev_locs[lang] = lang_dev_locs
        test_locs[lang] = set(lang_locs) - lang_dev_locs

    return dev_locs, test_locs


def filter_candidates(raw_candidates, subset):
    candidates = {
        lang: {loc: v for loc, v in cands.items() if loc in subset[lang]}
        for lang, cands in raw_candidates.items()
    }
    return candidates


def get_accuracy(correct_links, scores):
    accs = {}
    for lang, locs in scores.items():
        acc = 0
        total = 0
        for loc, candidates in locs.items():
            correct = correct_links[lang][loc]
            total += 1

            if not candidates:  # NIL
                if not correct:
                    acc += 1
                continue

            first = max(candidates, key=lambda x: x[1])[0]
            if first in correct:
                acc += 1

        accs[lang] = acc / total

    return accs


def acc_improved(accs, max_accs):
    return max_accs is None or all(accs[l] > max_accs[l] for l in accs)



def one_grid_search_run(candidates, stats, correct_links):
    max_accs = None

    coefs_grid = random.sample(COEFS_GRID, len(COEFS_GRID))
    grid_keys, grid_values = list(zip(*coefs_grid))
    coefs = {k: 1 for k in grid_keys}

    for key, values in zip(grid_keys, grid_values):
        max_val = 1
        for val in values:
            coefs[key] = val

            scores = score_candidates(candidates, stats, coefs)
            accs = get_accuracy(correct_links, scores)

            if acc_improved(accs, max_accs):
                max_accs = accs
                max_val = val

        coefs[key] = max_val

    return max_accs, coefs


def calculate_default(dev_locs, test_locs, info, correct_links):
    dev_candidates = filter_candidates(info['candidates'], dev_locs)
    test_candidates = filter_candidates(info['candidates'], test_locs)

    dev_scores = score_candidates(dev_candidates, info['stats'], DEFAULT)
    dev_acc = get_accuracy(correct_links, dev_scores)

    test_scores = score_candidates(test_candidates, info['stats'], DEFAULT)
    test_acc = get_accuracy(correct_links, test_scores)

    print(f'Coefficients: {DEFAULT}')
    print(f'Dev acc: {dev_acc}')
    print(f'Test acc: {test_acc}')


def grid_search(info, correct_links, dev_locs):
    overall_max_acc = None
    best_coefs = None

    candidates = filter_candidates(info['candidates'], dev_locs)

    for _ in range(50):
        max_acc, coefs = one_grid_search_run(candidates, info['stats'], correct_links)
        if best_coefs is None or acc_improved(max_acc, overall_max_acc):
            overall_max_acc = max_acc
            best_coefs = coefs

    print(f'Coefficients: {best_coefs}')
    print(f'Dev acc: {overall_max_acc}')
    return best_coefs


def evaluate(info, correct_links, coefs, test_locs):
    candidates = filter_candidates(info['candidates'], test_locs)
    scores = score_candidates(candidates, info['stats'], coefs)
    acc = get_accuracy(correct_links, scores)
    print(f'Test acc: {acc}')
    return acc


if __name__ == '__main__':
    with open(LOC_INFO_FILENAME) as f:
        info = json.load(f)

    correct_links = get_correct_links()
    dev_locs, test_locs = dev_test_split(correct_links)

    calculate_default(dev_locs, test_locs, info, correct_links)
    print()

    coefs = grid_search(info, correct_links, dev_locs)
    test_acc = evaluate(info, correct_links, coefs, test_locs)

    with open(COEFS_FILENAME, 'w') as f:
        json.dump(coefs, f, indent=2)


# Coefficients: {'n_labels': 1, 'n_descriptions': 1, 'n_sitelinks': 1, 'n_aliases': 1, 'n_statements': 1, 'n_qualifiers': 1, 'n_references': 1, 'n_links': 'log', 'label': 1, 'aliases': 1}
# Dev acc: {'ru': 0.7608695652173914, 'es': 0.6973684210526315}
# Test acc: {'ru': 0.6989247311827957, 'es': 0.7368421052631579}
#
# Coefficients: {'n_aliases': 0, 'n_references': 1, 'label': 4, 'n_qualifiers': 1, 'n_links': 0, 'n_descriptions': 1, 'n_sitelinks': 2, 'n_statements': 0, 'n_labels': 1, 'aliases': 3}
# Dev acc: {'ru': 0.8043478260869565, 'es': 0.7368421052631579}
# Test acc: {'ru': 0.7419354838709677, 'es': 0.7763157894736842}
