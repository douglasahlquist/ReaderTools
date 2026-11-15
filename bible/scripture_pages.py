#!/usr/bin/env python3
"""Builds Bible pages for the Chinese Reader app in one study language — a chapter, several, or
whole books — with that language's own reading aids. Chinese today: simplified Hanzi, pinyin and
the traditional Hanzi under them; Korean, Thai and others are added as language kits (bible/languages/).

    python3 bible/scripture_pages.py "Romans 12"                    # one chapter
    python3 bible/scripture_pages.py Romans                         # the whole book (16 pages)
    python3 bible/scripture_pages.py "Psalms 1-3" John              # chapter runs and books together
    python3 bible/scripture_pages.py "John 3" --with web            # an English row under each verse
    python3 bible/scripture_pages.py "John 3" --script traditional  # traditional first, simplified under it
    python3 bible/scripture_pages.py "John 3" --stdout              # print instead of writing
    python3 bible/scripture_pages.py --languages                    # the language kits there are

Pages go to ChineseReaderText/bible/passages/<book>-<chapter>.<edition>.md (john-3.chinese.md) and
are listed in the 经文 Passages list as that language's edition of the chapter. The texts come from
BibleSources; a book that isn't there yet gets the command to fetch it.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bible_pages as bp  # noqa: E402  (BibleSources, the Passages list, cells)
import languages  # noqa: E402

bs = bp.bs


def groups_for(verses, book, chapter, size, translations):
    """Verse groups: a translation's paragraphs when it has them, else runs of `size` verses."""
    starts = []
    for name in translations:
        starts = [v for v in bs.load(name, book)["paragraphs"].get(chapter, []) if v in verses]
        if starts:
            break
    if not starts:
        starts = verses[::size]
    if verses[0] not in starts:
        starts.insert(0, verses[0])
    out, current = [], []
    for v in verses:
        if v in starts and current:
            out.append(current)
            current = []
        current.append(v)
    out.append(current)
    return out


def build(kit, book, chapter, translations, size):
    rows = kit.verses(book, chapter)                     # {verse: [cell, …]} matching kit.columns
    extra = [(bs.VERSIONS[n]["label"], bp.version_text(n, book, chapter), bs.VERSIONS[n]["title"])
             for n in translations if bs.covers(n, book)]
    verses = sorted(set(rows).union(*[set(c[1]) for c in extra]))
    if not verses:
        raise SystemExit(f"No verses for {bs.BOOKS[book - 1][0]} {chapter}.")

    native, sound, english = kit.title(book, chapter)
    lines = [kit.page_settings, "", f"# {native} | {sound} | {english}", "",
             f"> **{kit.edition_title}** · " + " · ".join([kit.describe(book)] + [c[2] for c in extra]), ""]
    header = "| " + " | ".join(kit.columns + [c[0] for c in extra]) + " |"
    rule = "|" + "---|" * (len(kit.columns) + len(extra))
    for group in groups_for(verses, book, chapter, size, translations):
        lines += [kit.group_heading(group[0], group[-1]), "", "<!-- reader: table=verses -->", header, rule]
        for v in group:
            cells = rows.get(v, [""] * len(kit.columns))
            # The verse number goes in front of each of the language's own cells, as on the other pages.
            row = [f"{v} {c}".strip() if c else "" for c in cells] + [c[1].get(v, "") for c in extra]
            lines.append("| " + " | ".join(bp.cell(c) for c in row) + " |")
        lines.append("")
    for name in translations:
        if bs.VERSIONS[name].get("attribution"):
            lines += ["> " + bs.VERSIONS[name]["attribution"], ""]
    for note in kit.notices(book):
        lines += ["> " + note, ""]
    return "\n".join(lines).rstrip() + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("references", nargs="*", help='"Romans 12", Romans, "Psalms 1-3", "罗马书 12"')
    p.add_argument("--language", default="zh", help="language kit (default zh: Chinese)")
    p.add_argument("--script", default="both", help="Chinese: both (simplified, then traditional), "
                                                      "traditional (traditional, then simplified), simplified, traditional-only")
    p.add_argument("--with", dest="with_versions", default="", help="translation rows under each verse: web,kjv …")
    p.add_argument("--edition", help="the edition name in file names (default: the kit's, e.g. chinese)")
    p.add_argument("--keep-notes", action="store_true", help="keep the translation's small-print notes in the "
                                                                 "verses (Chinese: （或作…） （有古卷…）)")
    p.add_argument("--group", type=int, default=5, help="verses per group when no paragraphs are known (5)")
    p.add_argument("--text-repo", default=bp.default_text_repo(), help="the ChineseReaderText folder")
    p.add_argument("--no-index", action="store_true", help="don't update the 经文 Passages list")
    p.add_argument("--stdout", action="store_true", help="print the pages instead of writing them")
    p.add_argument("--languages", action="store_true", help="list the language kits, and stop")
    args = p.parse_args()

    if args.languages:
        for code, cls in languages.KITS.items():
            print(f"  {code:4} {cls.name:10} {cls.__doc__.strip().splitlines()[0]}")
        return
    if not args.references:
        p.error('give at least one reference, e.g. Romans or "Romans 12"')
    if args.language not in languages.KITS:
        p.error(f"no language kit “{args.language}” (have: {', '.join(languages.KITS)})")
    kit = languages.KITS[args.language](script=args.script, edition=args.edition, keep_notes=args.keep_notes)
    translations = [v.strip() for v in args.with_versions.split(",") if v.strip()]
    for name in translations:
        if name not in bs.VERSIONS:
            p.error(f"unknown version “{name}” (BibleSources: bible_fetch.py --known)")
    if not args.stdout and not os.path.isdir(os.path.join(args.text_repo, "bible")):
        p.error(f"no bible/ folder in {args.text_repo}: give --text-repo /path/to/ChineseReaderText")

    # Every source the pages need, checked before anything is written.
    refs = [bs.parse_reference(text) for text in args.references]
    missing = set()
    for book, *_ in refs:
        for need in kit.sources_needed(book) + [n for n in translations if bs.covers(n, book)]:
            if not os.path.exists(bs.source_path(need, book)):
                missing.add((need, bs.BOOKS[book - 1][0]))
    if missing:
        print("Not in BibleSources yet: " + ", ".join(f"{v} {b}" for v, b in sorted(missing)))
        books = sorted({b for _, b in missing})
        print(f"Fetch them first:  cd {bp.SOURCES_REPO} && python3 common/scripts/bible_fetch.py "
              f"{' '.join(repr(b) if ' ' in b else b for b in books)} --versions {','.join(sorted({v for v, _ in missing}))}")
        sys.exit(1)

    folder = os.path.join(args.text_repo, "bible", "passages")
    written = []
    for book, ch, ch2, v1, v2 in refs:
        if v1:
            print(f"  {bs.BOOKS[book - 1][0]} {ch}:{v1}: whole chapters only here — making chapter {ch}")
        chapters = kit.chapters(book) if ch is None else range(ch, (ch2 or ch) + 1)
        for chapter in chapters:
            page = build(kit, book, chapter, translations, args.group)
            if args.stdout:
                print(page)
                continue
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{bs.book_slug(book)}-{chapter}.{kit.edition}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
            written.append(os.path.relpath(path, args.text_repo))
    if len(written) > 6:
        print(f"wrote {len(written)} pages: {written[0]} … {written[-1]}")
    else:
        for path in written:
            print(f"wrote {path}")
    if written and not args.no_index:
        index, count = bp.rebuild_index(args.text_repo)
        print(f"listed {count} passages in {os.path.relpath(index, args.text_repo)}")


if __name__ == "__main__":
    main()
