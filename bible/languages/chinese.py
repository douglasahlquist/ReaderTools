"""Chinese: the 和合本 (Chinese Union Version, 1919) in simplified and traditional Hanzi, with pinyin."""
import os
import re

import bible_pages as bp

from .base import LanguageKit

bs = bp.bs


class ChineseKit(LanguageKit):
    """Simplified and traditional Hanzi with pinyin (和合本, Chinese Union Version 1919)."""

    code = "zh"
    name = "Chinese"
    page_settings = "<!-- reader: speak=word -->"
    EDITIONS = {
        "chinese": "中文 Chinese",                 # simplified, pinyin, then traditional
        "chinese-trad": "繁體 Traditional",        # traditional, pinyin, then simplified
        "chinese-simp": "简体 Simplified",         # simplified and pinyin only
        "chinese-trad-only": "繁體 Traditional only",
    }
    SCRIPTS = {"both": "chinese", "traditional": "chinese-trad", "simplified": "chinese-simp",
               "traditional-only": "chinese-trad-only"}

    # The CUV's small-print notes in the verse: （或作…） other renderings, （有古卷…） other manuscripts,
    # （原文作…） the original's wording. Left out unless --keep-notes.
    NOTE = re.compile(r"（(?:或作|或譯作|或译作|有古卷|原文作|原文是|又作|就是)[^）]*）")

    def __init__(self, script="both", edition=None, keep_notes=False):
        if script not in self.SCRIPTS:
            raise SystemExit(f"--script: one of {', '.join(self.SCRIPTS)}")
        self.script = script
        super().__init__(script, edition or self.SCRIPTS[script], keep_notes)
        # An edition named after a version (--edition kjv) is titled by the version's label (KJV).
        version = getattr(bp, "VERSIONS", {}).get(self.edition, {})
        self.edition_title = (self.EDITIONS.get(self.edition) or version.get("label")
                              or self.EDITIONS[self.SCRIPTS[script]])
        self.columns = {"both": ["Hanzi", "Pinyin", "繁體"], "traditional": ["Hanzi", "Pinyin", "简体"],
                        "simplified": ["Hanzi", "Pinyin"], "traditional-only": ["Hanzi", "Pinyin"]}[script]
        if not bp.HAVE_PINYIN:
            raise SystemExit("Pinyin needs pypinyin, jieba and OpenCC:  pip install -r requirements.txt")

    # The CUV as published (traditional): 'cuv' (downloaded) where BibleSources has the book,
    # else 'cut' (the Chinese Union traditional file imported from input/, all 66 books).
    def source(self, book):
        for version in ("cuv", "cut"):
            if version in bs.VERSIONS and os.path.exists(bs.source_path(version, book)):
                return version
        return "cuv"

    def sources_needed(self, book):
        return [self.source(book)]

    def chapters(self, book):
        return sorted(bs.load(self.source(book), book)["chapters"])

    def traditional(self, book, chapter):
        """{verse: traditional text}: only the space before 神 (a mark of respect) is kept."""
        out = {}
        for v, text in bs.load(self.source(book), book)["chapters"].get(chapter, {}).items():
            if not self.keep_notes:
                text = self.NOTE.sub("", text)
            text = re.sub(r"\s+(?=神)", "\u0001", text)
            out[v] = re.sub(r"\s+", "", text).replace("\u0001", " ")
        return out

    def verses(self, book, chapter):
        rows = {}
        for v, trad in self.traditional(book, chapter).items():
            simp = bp.to_simplified(trad).replace("著", "着")   # the CUV's 著 is the particle 着
            simp_spaced, pinyin = bp.hanzi_and_pinyin(simp)      # pinyin works from the simplified
            trad_spaced = bp.same_words(simp_spaced, trad)       # same words, same pinyin
            rows[v] = {
                "both": [simp_spaced, pinyin, trad_spaced],
                "traditional": [trad_spaced, pinyin, simp_spaced],
                "simplified": [simp_spaced, pinyin],
                "traditional-only": [trad_spaced, pinyin],
            }[self.script]
        return rows

    def title(self, book, chapter):
        en, zh, py, _ = bs.BOOKS[book - 1]
        native = bp.to_traditional(zh) if self.script.startswith("traditional") and bp.to_traditional else zh
        return f"{native} {chapter}", f"{py} {chapter}", f"{en} {chapter}"

    def group_heading(self, first, last):
        nums = f"{first}" if first == last else f"{first}–{last}"
        return f"## 第{nums}节 | Dì {nums} jié | {'Verse' if first == last else 'Verses'} {nums}"

    def describe(self, book):
        scripts = {"both": "simplified and traditional", "traditional": "traditional and simplified",
                   "simplified": "simplified", "traditional-only": "traditional"}[self.script]
        return f"和合本 (Chinese Union Version, 1919), {scripts}"
