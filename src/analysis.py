from pathlib import Path
import json
import re
import os 
import math

#import spacy
from pdfminer.high_level import extract_pages, LTPage

def expand_hyphen(word: str) -> list[str]:

    out = []

    if '-' in word:
        [first, second] = word.split('-', maxsplit=2)
        out.append(first + second)
        out.append(first + " " + second)

    return out 

def expand_plural(word: str) -> list[str]:

    out = []

    if word[-1] == 'y':
        out.append(word[:-1] + "ies")
    else:
        out.append(word + 's')

    return out

def expand_case(word: str) -> list[str]:

    out = []

    # Genetive
    if word[-1] == 's':
        out.append(word + 'es')
    else:
        out.append(word + 's')

    # Dative
    if word[-1] != 's':
        out.append(word + 'n')

    return out


def expand_gender(word: str) -> list[str]:

    out = []

    out.append(word + 'in')
    out.append(word + 'innen')
    return out 


def expand_noun(word: str) -> list[str]:
    out = []

    out.extend(expand_hyphen(word))
    out.extend(expand_plural(word))
    out.extend(expand_case(word))
    out.extend(expand_gender(word))






def calc_entropy(anglicism: str, words: list[str]) -> float:
    #TODO: count only nouns adjectives adverbs verbs
    # [blah ang] [blah blah ang word word]
    # count occurences in the window
    counts = {}
    for word in words:
        # skip if its the anglicism 
        if word == anglicism:
            continue
        # increment if already seen
        if word in counts.keys():
            counts[word] += 1
        # add if not already seen
        else:
            counts[word] = 1

    # total number of words seen
    total = sum(counts.values())
    entropy = 0
    # calculate probabilities 
    for count in counts.values():
        # entropy += probability * log_2(probability)
        entropy += count/total * math.log(count/total, 2)

    return -entropy

def find_angilicisms(video: dict, anglicisms: list[str]):
    #TODO: generate endings to match against
    ENTROPY_WINDOW_SIZE = 25
    result = {}
    entropies = []
    t = video['transcript'].split()

    for ang in anglicisms: 
        # ignore small ones (likely to be wrong)
        if len(ang) < 3:
            continue
        if ang in t:
            # find index of the anglicism
            ind = t.index(ang)
            # clamp lower and upper bounds to not go out of the list
            lower = max(0, ind-ENTROPY_WINDOW_SIZE)
            upper = min(len(t), ind+ENTROPY_WINDOW_SIZE)
            entropies.append( (ang, calc_entropy(ang, t[lower:upper])) )
            if ang in result.keys():
                result[ang] += 1 
            else:
                result[ang] = 1

    return result, entropies


def tagging():
    nlp = spacy.load("de_dep_news_trf")
    for p in Path("output/").glob("*.json"):
        channel = json.loads(p.read_text())
        transcripts = [v['transcript'] for v in channel['transcripts']]
        for transcript in transcripts[:1]:
            doc = nlp(transcript)
            for token in doc:
                print(f'{token.text}: {token.pos_} {token.pos}')


def scrape_pdf():
    pdf = extract_pages('input/anglicisms.pdf')
    anglicisms = set()
    for i, page in enumerate(pdf):
        # page number 14 is horribly formatted, page number 425 is blank.
        if i == 13 or i == 424:
            continue

        # main text box is second to last on each page, always followed by textbox containing page number
        box = list(page)[-2]
        for line in box:
            word = ''
            # build up the anglicism by getting all the letters from the beginning of the line until it stops being bold 
            for letter in line:
                if hasattr(letter, 'fontname'):
                    if 'Bold' in letter.fontname:
                        word += letter._text
                    # once non bold character is found save the word and move on to the next line
                    else:
                        # remove incase the : was bold
                        word.replace(':', '')
                        # deal with whitespace
                        word = word.strip()
                        # some lines have two similar anglicisms seperated by a ,
                        # if this is one of them add both to the list
                        if ',' in word:
                            words = word.split(',')
                            words = [w.strip() for w in anglicisms]
                            for w in words:
                                anglicisms.add(w)
                        # make sure word is not blank 
                        elif word != '':
                            anglicisms.add(word)
                        # next line 
                        break
    return anglicisms


def main():
    anglicisms = []
    if os.path.exists('output/anglicisms.txt'):
        with open('output/anglicisms.txt', 'r') as f:
            lines = f.readlines()
            anglicisms = [l.strip() for l in lines]
    else:
        anglicisms = scrape_pdf()
        with open('output/anglicisms.txt', 'w') as f:
            for a in anglicisms:
                f.write(f'{a}\n')

    all_anglicisms = []
    all_entropies = []
    for p in Path("output/").glob("*.json"):
        channel = json.loads(p.read_text())
        transcripts = channel['transcripts']
        print(f'channel: {channel["id"]}')
        for t in transcripts:
            angs, entropies = find_angilicisms(t, anglicisms)
            all_anglicisms.append(angs)
            all_entropies.append(entropies)

    top15_angs = sorted(all_anglicisms, key=lambda x: sum(x.values()), reverse=True)[:15]
    top15_ents = sorted(all_entropies, key=len, reverse=True)[:15]
    for a, e in zip(top15_angs, top15_ents):
        print("\n\nresult:")
        print(a)
        print(e)
    #tagging()


if __name__ == '__main__':
    main()
