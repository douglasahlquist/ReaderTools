"""A starting point for another language kit: copy to korean.py (or thai.py …), fill in each
method, and add the class to KITS in __init__.py. See chinese.py for a complete kit.

Korean (planned): the text is Hangul with spaces between words, so each word is a unit; the sound
line is Revised Romanization (e.g. the `korean-romanizer` package); the second script can be the
Hanja for Sino-Korean words (e.g. the `hanja` package). Source: krv (개역한글, public domain).

Thai (planned): Thai has no spaces between words, so verses are split into words first (PyThaiNLP's
word_tokenize); the sound line is RTGS or Paiboon romanization (PyThaiNLP's romanize). Source: thkjv
(CC BY-NC-ND 4.0: keep the Thai words unchanged and add the notice from notices()).
"""
from .base import LanguageKit


class TemplateKit(LanguageKit):
    """(one line: what this kit shows)"""

    code = "xx"
    name = "Language"
    page_settings = "<!-- reader: speak=word -->"
    EDITIONS = {"language": "Language"}

    def __init__(self, script="both", edition=None):
        super().__init__(script, edition)
        self.columns = ["Text", "Romanization"]   # the app reads the first column as the text line

    def sources_needed(self, book):
        return ["krv"]

    def chapters(self, book):
        raise NotImplementedError

    def verses(self, book, chapter):
        raise NotImplementedError

    def title(self, book, chapter):
        raise NotImplementedError

    def describe(self, book):
        raise NotImplementedError
