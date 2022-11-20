import re
import os


# Evaluate NER performance on the plays;
# Create `final` folder with unified annotations for further usage.


AUTO_LOC_REGEX = re.compile(r'<loc>.+?</loc>')
MANUAL_LOC_REGEX = re.compile(r'{{(.+?)}}')

AUTO_CORPUS_FOLDER = os.path.join('corpus', 'autoparsed')
FIXED_CORPUS_FOLDER = os.path.join('corpus', 'fixed')
FINAL_CORPUS_FOLDER = os.path.join('corpus', 'final')
LANGS = ['rus', 'span']


for lang in LANGS:
    n = 0
    locs_in_auto = 0
    left_locs_in_fixed = 0
    manual_locs_in_fixed = 0

    os.makedirs(os.path.join(FINAL_CORPUS_FOLDER, lang), exist_ok=True)

    for filename in os.listdir(os.path.join(AUTO_CORPUS_FOLDER, lang)):
        if not filename.endswith('.xml'):
            continue

        with open(os.path.join(AUTO_CORPUS_FOLDER, lang, filename)) as f:
            auto_play = f.read()

        if not os.path.exists(os.path.join(FIXED_CORPUS_FOLDER, lang, filename)):
            continue

        n += 1
        with open(os.path.join(FIXED_CORPUS_FOLDER, lang, filename)) as f:
            fixed_play = f.read()

        locs_in_auto += len(AUTO_LOC_REGEX.findall(auto_play))
        left_locs_in_fixed += len(AUTO_LOC_REGEX.findall(fixed_play))
        manual_locs_in_fixed += len(MANUAL_LOC_REGEX.findall(fixed_play))

        final_play = MANUAL_LOC_REGEX.sub('<loc from="manual">\\1</loc>', fixed_play)
        with open(os.path.join(FINAL_CORPUS_FOLDER, lang, filename), 'w') as f:
            f.write(final_play)

    precision = left_locs_in_fixed / locs_in_auto
    recall = left_locs_in_fixed / (left_locs_in_fixed + manual_locs_in_fixed)
    print(f'{lang}, {n} plays\nprecision: {precision}\nrecall: {recall}\n')


# Evaluation results:
#
# rus, 10 plays
# precision: 0.6623376623376623
# recall: 0.9553314121037464
#
# span, 10 plays
# precision: 0.739961759082218
# recall: 0.979746835443038
