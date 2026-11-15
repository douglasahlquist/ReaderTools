"""Language kits for scripture_pages.py: one per study language.

A kit turns a chapter of a Bible version into the cells of the app's verse table for that
language — the text, its sound line, and any second script — plus the page's titles. To add a
language, copy template.py to <language>.py, fill it in, and list the class in KITS below.
"""
from .chinese import ChineseKit

KITS = {
    "zh": ChineseKit,
    # "ko": KoreanKit,   (template.py: Hangul, Revised Romanization, Hanja for Sino-Korean words)
    # "th": ThaiKit,     (template.py: words split with PyThaiNLP, RTGS or Paiboon romanization)
}

# Edition names the kits write (romans-12.chinese.md) → their title in the Passages list.
EDITION_TITLES = {}
for _kit in KITS.values():
    EDITION_TITLES.update(_kit.EDITIONS)
