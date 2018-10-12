import subprocess
import re
import random
import time
import sys
import os


def keep(w):
    exclusions = [
        '\\x',  # Probably unicode literal
        '.svg',  # Links to file
        '.png',
        '.jpg',
        '.jpeg',
        ':',  # Colons often singal meta pages (users, categories, etc.)
        '/'  # Forward slashes are a problem for file-system navigation
    ]

    if any(exclusion in w for exclusion in exclusions):
        return False

    return True

def filter(w):

    # Filter link aliases
    index = w.find('|')
    if index >= 0:
        w = w[:index]

    # Filter page chapter links
    index = w.find('#')
    if index >= 0:
        w = w[:index]

    return w

start_time = time.time()

# Open dev/null to pipe wget output
FNULL = open(os.devnull, 'w')

url_base = 'https://en.wikipedia.org/wiki/Special:Export/{}'
dir_base = 'xml/{}.xml'
corpus_base = 'corpus/{}.corpus'

# With computation time this evaluates to 1 request per second for small
# searches. For larger searches, it is slightly less frequent than that.
sleep_time = 0.8

# Initialize bookkeeping objects
checked = set()
url_dict = {}

# Set defaults and basic CLI args parsing
start = 'effective_field_theory'
start_url = start

article_limit = 60
limit_reached = False

if len(sys.argv) > 1:
    start = sys.argv[1].lower()
    start_url = sys.argv[1]

if len(sys.argv) > 2:
    article_limit = int(sys.argv[2])

# Set seed for scraping
seed = start
url_dict[start] = start_url
checked.add(start)

for x in range(article_limit):
    try:
        subprocess.call(['wget', '-O', dir_base.format(seed),
                         url_base.format(url_dict[seed])], stdout=FNULL,
                        stderr=subprocess.STDOUT)

        with open(dir_base.format(seed), 'r') as f:
            lines = [x.rstrip() for x in f]
            text = '\n'.join(lines)

        if '<page>' not in text:
            raise OSError('{} not valid article'.format(seed))

        with open(corpus_base.format(seed), 'w') as f:
            subprocess.call(['perl', 'wiki2text.pl', dir_base.format(seed)],
                            stdout=f)

        if not limit_reached:

            matches = re.findall('\[\[(.*?)\]\]', text)
            matches = {s.lower().replace(' ', '_'): s.replace(' ', '_') for s in
                    matches}
            filtered = {filter(s): filter(t) for s, t in matches.items() if
                        keep(s) and s not in checked}

            url_dict.update(filtered)

            limit_reached = len(url_dict) + len(checked) > article_limit * 1.15

            if limit_reached:
                print('Limit reached!')
                print('time: {} seconds'.format(time.time() - start_time))
                print('iterations: {}'.format(x + 1))
                print('size of url_dict: {}'.format(len(url_dict)))
                print('size of checked: {}'.format(len(checked)))
                checked = {}

        del url_dict[seed]

        seed = random.choice(list(url_dict))

        if not limit_reached:
            checked.add(seed)

        time.sleep(sleep_time)

    except OSError:
        print('Warning: broken link checked, {} -> {}'.format(seed,
                                                              url_dict[seed]))
        # delete created file if it exists
        del url_dict[seed]
        seed = random.choice(list(url_dict))
        time.sleep(sleep_time)

# Close reference to devnull
FNULL.close()

seconds = time.time() - start_time
print('Completed in {} seconds.'.format(seconds))
print('Percent time computing: {}'.format((seconds - article_limit * sleep_time)/seconds))

