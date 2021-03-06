from __future__ import unicode_literals
import re

from collections import namedtuple
from six import string_types

from prompt_toolkit.completion import Completer, Completion

__all__ = [
    'FuzzyWordCompleter',
]


class FuzzyWordCompleter(Completer):
    """
    Fuzzy completion on a list of words.

    If the list of words is: ["leopard" , "gorilla", "dinosaur", "cat", "bee"]
    Then trying to complete "oar" would yield "leopard" and "dinosaur", but not
    the others, because they match the regular expression 'o.*a.*r'.

    The results are sorted by relevance, which is defined as the start position
    and the length of the match.

    See: https://blog.amjith.com/fuzzyfinder-in-10-lines-of-python

    :param words: List of words or callable that returns a list of words.
    :param meta_dict: Optional dict mapping words to their meta-information.
    :param WORD: When True, use WORD characters.
    :param sort_results: Boolean to determine whether to sort the results (default: True).

    Fuzzy algorithm is based on this post: https://blog.amjith.com/fuzzyfinder-in-10-lines-of-python
    """
    def __init__(self, words, meta_dict=None, WORD=False, sort_results=True):
        assert callable(words) or all(isinstance(w, string_types) for w in words)

        self.words = words
        self.meta_dict = meta_dict or {}
        self.sort_results = sort_results
        self.WORD = WORD

    def get_completions(self, document, complete_event):
        # Get list of words.
        words = self.words
        if callable(words):
            words = words()

        word_before_cursor = document.get_word_before_cursor(WORD=self.WORD)

        fuzzy_matches = []
        pat = '.*?'.join(map(re.escape, word_before_cursor))
        pat = '(?=({0}))'.format(pat)   # lookahead regex to manage overlapping matches
        regex = re.compile(pat, re.IGNORECASE)
        for word in words:
            matches = list(regex.finditer(word))
            if matches:
                # Prefer the match, closest to the left, then shortest.
                best = min(matches, key=lambda m: (m.start(), len(m.group(1))))
                fuzzy_matches.append(_FuzzyMatch(len(best.group(1)), best.start(), word))

        def sort_key(fuzzy_match):
            " Sort by start position, then by the length of the match. "
            return fuzzy_match.start_pos, fuzzy_match.match_length

        fuzzy_matches = sorted(fuzzy_matches, key=sort_key)

        for match in fuzzy_matches:
            display_meta = self.meta_dict.get(match.word, '')

            yield Completion(
                match.word,
                -len(word_before_cursor),
                display_meta=display_meta,
                display=self._get_display(match, word_before_cursor))

    def _get_display(self, fuzzy_match, word_before_cursor):
        """
        Generate formatted text for the display label.
        """
        m = fuzzy_match

        if m.match_length == 0:
            # No highlighting when we have zero length matches (no input text).
            return m.word

        result = []

        # Text before match.
        result.append(('class:fuzzymatch.outside', m.word[:m.start_pos]))

        # The match itself.
        characters = list(word_before_cursor)

        for c in m.word[m.start_pos:m.start_pos + m.match_length]:
            classname = 'class:fuzzymatch.inside'
            if characters and c == characters[0]:
                classname += '.character'
                del characters[0]

            result.append((classname, c))

        # Text after match.
        result.append(
            ('class:fuzzymatch.outside', m.word[m.start_pos + m.match_length:]))

        return result


_FuzzyMatch = namedtuple('_FuzzyMatch', 'match_length start_pos word')
