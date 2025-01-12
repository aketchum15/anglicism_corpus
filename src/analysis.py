from pathlib import Path
import argparse
import code
import json
import os 
import pandas as pd
import pickle
import requests
import sys

from bs4 import BeautifulSoup
from pdfminer.high_level import extract_pages

from Anglicism import Anglicism

ANGLICISIMS_PKL_PATH = 'output/anglicisms.pkl'

def find_angilicisms(video: dict, anglicisms: list[Anglicism]):

    ENTROPY_WINDOW_SIZE = 25
    result = {}
    entropies = []
    transcript = video['transcript'].split()

    found = []

    for ang in anglicisms: 
        if not isinstance(ang, Anglicism):
            print(f'{ang} wrong type')
        # ignore small ones (likely to be garbage)
        if len(ang.ang) < 3:
            continue

        # check against each form of the anglicism
        if ang in transcript:
            # if its found save the index in the transcript where it was
            found.append( (ang, transcript.index(ang)) )

    # sort the found list by the indicies
    found = sorted(found, key=lambda x : x[1])
    # calculate entropies for all found anglicisms
    for i, (ang, index) in enumerate(found):
        # get the anglicism that was found 
        # calculate bounds for entropy window
        lower = max(0, index-ENTROPY_WINDOW_SIZE)
        upper = min(len(transcript), index+ENTROPY_WINDOW_SIZE)

        # this will ensure no overlap in windows
        # ex: [blah blah blah ang1 blah blah][ang2 blah blah blah][ang3 blah blah] 
        if (i < len(found)-1 and found[i+1][1] < upper):
            upper = found[i+1][1]

        # calculate
        entropies.append( (ang, ang.calc_entropy(transcript[lower:upper])) )
        if ang.ang in result.keys():
            result[ang.ang] += 1 
        else:
            result[ang.ang] = 1
            
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


def scrape_website(url: str) -> set[str]:

    print(f'Scraping website: {url}')

    out = set()
    # get the webpage contents.
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    # the class for the div containing the anglicisms
    p_tags = soup.find('div', class_='mw-body-content').find_all('p')
    for p in p_tags[:-3]:
        # find all the a tags in each p tag, these are where the anglicisms are 
        a_tags = p.find_all('a', recursive=False)
        for a in a_tags:
            word = a.text.replace(':', '').strip()
            out.add(word)

    print(f'{len(out)} anglicisms scraped.')
    return out 

def scrape_pdf(path: str)  -> set[str]:

    print(f'Scraping pdf: {path}')

    pdf = extract_pages(path)
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

    print(f'{len(anglicisms)} anglicisms scraped.')
    return anglicisms


def get_anglicisms() -> list[Anglicism]:

    # anglicisms are stored as a dictionary containing the anglicism and its part of speech
    ANGLICISIMS_PDF_PATH = 'input/anglicisms.pdf'
    ANGLICISIMS_WEBSITE_URL = 'https://de.wiktionary.org/wiki/Verzeichnis:Deutsch/Anglizismen'

    # ensure output folder exists
    if not os.path.exists('output/'):
        os.mkdir('output')

    anglicisms: list[Anglicism] = []
    if os.path.exists(ANGLICISIMS_PKL_PATH):
        with open(ANGLICISIMS_PKL_PATH, 'rb') as f:
            print('Using existing anglicisms.pkl file')
            anglicisms = pickle.load(f)
    else:
        print('anglicisms.pkl not found, scraping...')
        # get anglicisms from the pdf
        pdf_anglicisms = scrape_pdf(ANGLICISIMS_PDF_PATH)
        # get anglicisms from the website
        website_anglicisms = scrape_website(ANGLICISIMS_WEBSITE_URL)
        # merge the two sets (union ensures no repeats) and sort
        scraped_angs = sorted(website_anglicisms.union(pdf_anglicisms))
        for ang in scraped_angs:
            anglicisms.append(Anglicism(ang))

        print(f'{len(anglicisms)} unique anglicisms scraped.')

        with open(ANGLICISIMS_PKL_PATH, 'wb') as f:
            pickle.dump(anglicisms, f)
        print(f'Anglicisms written to file: {ANGLICISIMS_PKL_PATH}.')

    return anglicisms

def get_transcripts():
    channels = []
    for p in Path("output/").glob("*.json"):
        channel = json.loads(p.read_text())
        channels.append(channel)

    return channels

def analyze():
    all_anglicisms = []
    all_entropies = []

    angs = get_anglicisms()
    transcripts = get_transcripts()
    for channel in transcripts:
        videos = channel['transcripts']
        for v in videos:
            found_angs, entropies = find_angilicisms(v, angs)
            all_anglicisms.append(found_angs)
            all_entropies.append(entropies)

    top15_angs = sorted(all_anglicisms, key=lambda x: sum(x.values()), reverse=True)[:15]
    top15_ents = sorted(all_entropies, key=len, reverse=True)[:15]
    for a, e in zip(top15_angs, top15_ents):
        print("\n\nresult:")
        print(a)
        print(e)

def edit():
    angs = get_anglicisms()
    df = pd.DataFrame([vars(a) for a in angs])
    def save_and_exit():
        print('Saving changes made to anglicisms')
        angs_out = [Anglicism(ang, pos) for (ang, pos) in zip(df['ang'], df['pos'])]
        with open(ANGLICISIMS_PKL_PATH, 'wb') as f:
            pickle.dump(angs_out, f)
        sys.exit(0)

    l = globals().copy()
    l.update(locals())
    l['exit'] = save_and_exit
    print('''
          You are now in interactive mode, 
          the list of anglicisms can be accessed through the variable "df". 
          use exit() to save changes and exit, use quit() to exit without saving changes.
          ''')

    code.interact(local=l)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='Corpus Analysis')
    parser.add_argument("command", choices=["analyze", "explore"], 
                        help="The command to execute (either 'analyze' or 'edit').")

    args = parser.parse_args()

    if args.command == 'analyze':
        analyze()
    elif args.command == 'edit':
        edit()
