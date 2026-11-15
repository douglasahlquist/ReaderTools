"""What every language kit provides (see chinese.py for a complete one)."""


class LanguageKit:
    """One study language: how its verses become the cells of the app's verse table."""

    code = ""                 # "zh", "ko", "th" …
    name = ""                 # "Chinese"
    page_settings = ""        # the page's <!-- reader: … --> line, e.g. speak=word
    EDITIONS = {}             # edition name (in file names) → title in the Passages list

    def __init__(self, script="both", edition=None, keep_notes=False):
        self.keep_notes = keep_notes
        self.edition = edition or next(iter(self.EDITIONS))
        self.edition_title = self.EDITIONS.get(self.edition, self.edition.capitalize())
        self.columns = []     # the table's own columns, e.g. ["Hanzi", "Pinyin", "繁體"]

    def sources_needed(self, book):
        """The BibleSources versions this kit reads for a book (checked before building)."""
        raise NotImplementedError

    def chapters(self, book):
        """Every chapter of a book that the source has."""
        raise NotImplementedError

    def verses(self, book, chapter):
        """{verse: [cell for each of self.columns]} — without verse numbers."""
        raise NotImplementedError

    def title(self, book, chapter):
        """(in the language, its sound line, English): ("罗马书 12", "Luó mǎ shū 12", "Romans 12").
        The English part must stay a plain reference: the Passages list reads it."""
        raise NotImplementedError

    def group_heading(self, first, last):
        """The heading over a group of verses, e.g. "## 第1–2节 | Dì 1–2 jié | Verses 1–2"."""
        nums = f"{first}" if first == last else f"{first}–{last}"
        return f"## {nums} | {nums} | {'Verse' if first == last else 'Verses'} {nums}"

    def describe(self, book):
        """The version(s) the page shows, for its first line."""
        raise NotImplementedError

    def notices(self, book):
        """Copyright or attribution lines the version needs at the end of the page."""
        return []
