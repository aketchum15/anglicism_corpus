import math

import spacy

NLP = None

class Anglicism:

    def __init__(self, ang: str, pos: str|None = None) -> None:

        self.ang = ang
        global NLP
        if not pos:
            if not NLP:
                NLP = spacy.load("de_dep_news_trf")
            doc = NLP(ang)
            self.pos = doc[0].pos_
        else:
            self.pos = pos

        self.morphologies = [self.ang]

        if self.pos == 'VERB':
            expand_inf = lambda word: [word + 'en', word + 'n', word + 'len', word + 'eln']
            expand_present = lambda word: [word + 'e', word + 'st', word + 'et', word + 't', word + 'en', word + 'n']
            expand_past = lambda word: [word + 'te', word + 'ete', word + 'test', word + 'etest', word + 'ten', word + 'eten', word + 'tet', word + 'etet']
            expand_partizip = lambda word: [word + 'd']
            expand_perfect = lambda word: ['ge' + word + 't', 'ge' + word + 'ed', word + 't', word + 'ed']
            self.morphologies.extend(expand_inf(self.ang))
            self.morphologies.extend(expand_present(self.ang))
            self.morphologies.extend(expand_past(self.ang))
            self.morphologies.extend(expand_partizip(self.ang))
            self.morphologies.extend(expand_perfect(self.ang))

        elif self.pos == 'NOUN':
            def expand_hyphen(word: str) -> list[str]:
                out = []
                if '-' in word:
                    [first, second] = word.split('-', maxsplit=1)
                    out.append(first + second)
                    out.append(first + " " + second)
                return out 

            expand_gender = lambda word: [word + 'in', word + 'innen']
            expand_case = lambda word: [word + 'es' if word[-1] == 's' else word + 's', word + 'n']
            expand_plural = lambda word: [word[:-1] + 'ies' if word[-1] == 'y' else word + 's']

            self.morphologies.extend(expand_hyphen(self.ang))
            self.morphologies.extend(expand_plural(self.ang))
            self.morphologies.extend(expand_case(self.ang))
            self.morphologies.extend(expand_gender(self.ang))

        elif self.pos == 'ADJ':
            expand_attributive = lambda word: [word + 'e', word + 'n', word + 'en']
            expand_comparative = lambda word: [word + 'r', word + 'er', word + 're', word + 'ere', word + 'ren', word + 'eren']
            expand_superlative = lambda word: [word + 'sten', word + 'esten', word + 'ste', word + 'este']
            def expand_intensifiers(word):
                out = []
                for prefix in ['super', 'ultra', 'mega']:
                    out.append(prefix + word + 'e')
                    out.append(prefix + word + 'en')
                    out.append(prefix + word + 'n')
                    out.append(prefix + word + 'er')
                    out.append(prefix + word + 'r')

                out.extend([word + 'rweise', word + 'erweise'])
                return out

            self.morphologies.extend(expand_attributive(self.ang))
            self.morphologies.extend(expand_comparative(self.ang))
            self.morphologies.extend(expand_superlative(self.ang))
            self.morphologies.extend(expand_intensifiers(self.ang))


    def __repr__(self) -> str:
        return f'{self.ang}: {self.pos}'


    # this over rides how python compares an Anglicism object
    def __eq__(self, value: object, /) -> bool:
        # if the thing this is being compared to is any of the morphologies then it is equal to this anglicism
        return value in self.morphologies


    def calc_entropy(self, words: list[str]) -> float:
        # count occurences in the window
        counts = {}
        for word in words:
            # skip if its the anglicism 
            if word == self:
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
