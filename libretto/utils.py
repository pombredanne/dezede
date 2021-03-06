# coding: utf-8

from __future__ import unicode_literals
import re
from unicodedata import normalize
from .models.functions import hlp


__all__ = (
    'abbreviate',
)


def remove_diacritics(string):
    return normalize('NFKD', string).encode('ASCII', 'ignore')


def is_vowel(string):
    return remove_diacritics(string) in b'AEIOUYaeiouy'


def chars_iterator(s):
    i0 = 0
    c0 = s[0]
    i1 = 1
    out = []
    for c1 in s[1:-1]:
        out.append((i0, c0, i1, c1))
        i0 = i1
        c0 = c1
        i1 += 1
    return out


# TODO: créer un catalogue COMPLET de ponctuations de séparation.
ABBREVIATION_RE = re.compile('(-|\.|\s)')


def abbreviate(string, min_vowels=0, min_len=1, tags=True, enabled=True):
    """
    Abrège les mots avec une limite de longueur (par défaut 0).

    >>> print(abbreviate('amélie'))
    <span title="Amélie">a.</span>
    >>> print(abbreviate('jeanöõ-françois du puy du fou', tags=False))
    j.-fr. du p. du f.
    >>> print(abbreviate('autéeur dramatique de la tour de babel', 1,
    ...                  tags=False))
    a. dram. de la tour de bab.
    >>> print(abbreviate('adaptateur', 1, 4, tags=False))
    adapt.
    >>> print(abbreviate('Fait à Quincampoix', 2, tags=False))
    Fait à Quincamp.
    >>> print(abbreviate('ceci est un test bidon', enabled=False))
    ceci est un test bidon
    """

    if not enabled:
        return string

    out = ''
    for i, sub in enumerate(ABBREVIATION_RE.split(string)):
        if not i % 2:
            if not sub:
                continue
            vowels_count = min_vowels
            vowel_first = is_vowel(sub[0])
            if vowel_first:
                vowels_count -= 1
            for j0, c0, j1, c1 in chars_iterator(sub):
                general_case = is_vowel(c1) and not is_vowel(c0)
                particular_case = j0 == 0 and vowel_first
                if general_case or particular_case:
                    if vowels_count <= 0:
                        if min_len <= j1:
                            sub = sub[:j1] + '.'
                            break
                    if general_case:
                        vowels_count -= 1
        out += sub
    return hlp(out, string, tags)
