#!/usr/bin/env python3
"""Downloads Bible texts into ChineseReaderTools/sources/, one file per version per book, ready to
check in. bible_pages.py then builds pages from those files without going online.

    python3 bible/bible_fetch.py Romans Psalms                 # the versions editions.json uses
    python3 bible/bible_fetch.py Romans --versions kjv,tr      # these versions only
    python3 bible/bible_fetch.py --nt --versions sblgnt        # the whole New Testament
    python3 bible/bible_fetch.py --all                         # every book, every edition's versions
    python3 bible/bible_fetch.py --list                        # what is in sources/ now
    python3 bible/bible_fetch.py Romans --refresh              # download again

Books can be named in English or Chinese (罗马书), and a reference like "Romans 12" fetches its
book. A version that doesn't cover a book (Greek in the Old Testament, Hebrew in the New) is
skipped. The large upstream files are kept in ~/.cache/chinesereader-bible so a second fetch
is quick; sources/ holds only the cleaned books.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bible_sources as bs  # noqa: E402

EDITIONS = os.path.join(bs.HERE, "editions.json")


def edition_versions():
    """Every version some edition in editions.json uses."""
    with open(EDITIONS, encoding="utf-8") as f:
        editions = json.load(f)["editions"]
    names = []
    for edition in editions.values():
        for lang in ("zh", "en", "greek", "hebrew"):
            for name in edition.get(lang, "").split(","):
                name = name.strip()
                if name in ("cuv-trad",):
                    name = "cuv"
                if name and name != "none" and name not in names:
                    names.append(name)
    return names


def list_sources():
    found = False
    for version in bs.VERSIONS:
        books = bs.available_books(version)
        if not books:
            continue
        found = True
        names = ", ".join(bs.BOOKS[b - 1][0] for b in books) if len(books) <= 8 else f"{len(books)} books"
        print(f"  {version:10} {names}")
    if not found:
        print("  (nothing yet)")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("books", nargs="*", help='e.g. Romans, "1 Corinthians", 诗篇, "Romans 12"')
    p.add_argument("--versions", help="comma-separated (default: every version editions.json uses)")
    p.add_argument("--ot", action="store_true", help="every Old Testament book")
    p.add_argument("--nt", action="store_true", help="every New Testament book")
    p.add_argument("--all", action="store_true", help="every book")
    p.add_argument("--refresh", action="store_true", help="download again even if the book is in sources/")
    p.add_argument("--list", action="store_true", help="show what is in sources/ and stop")
    args = p.parse_args()

    print(f"sources: {bs.SOURCES}")
    if args.list:
        list_sources()
        return

    versions = [v.strip() for v in (args.versions or ",".join(edition_versions())).split(",") if v.strip()]
    versions = ["cuv" if v == "cuv-trad" else v for v in versions]
    unknown = [v for v in versions if v not in bs.VERSIONS]
    if unknown:
        p.error(f"unknown version(s): {', '.join(unknown)}. Known: {', '.join(bs.VERSIONS)}")

    books = []
    if args.all or args.ot:
        books += list(bs.OLD_TESTAMENT)
    if args.all or args.nt:
        books += list(bs.NEW_TESTAMENT)
    for name in args.books:
        book = bs.parse_reference(name)[0]
        if book not in books:
            books.append(book)
    if not books:
        p.error("name at least one book (e.g. Romans), or --ot, --nt or --all")

    written = skipped = 0
    for version in versions:
        for book in sorted(set(books)):
            if not bs.covers(version, book):
                continue
            path = bs.source_path(version, book)
            if os.path.exists(path) and not args.refresh:
                skipped += 1
                continue
            chapters, paragraphs = bs.fetch_book(version, book)
            if not chapters:
                print(f"  {version}: no {bs.BOOKS[book - 1][0]} upstream")
                continue
            bs.save(version, book, chapters, paragraphs)
            written += 1
            print(f"  {version:10} {bs.BOOKS[book - 1][0]:16} {len(chapters)} chapters → "
                  f"{os.path.relpath(path, os.path.dirname(bs.SOURCES))}")
    print(f"{written} written, {skipped} already there (--refresh to download again)")


if __name__ == "__main__":
    main()
