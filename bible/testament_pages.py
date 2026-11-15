"""What new_testament.py and old_testament.py share: one page per chapter with simplified Hanzi,
pinyin and traditional Hanzi, the original language, an English version and the other languages
(Korean, Vietnamese, Thai, French, German) under each verse. The app shows the ones the user
picks (Settings › Bible Versions).

Nothing is added twice: a chapter whose page already has every column is left alone; a page
missing some is rebuilt in place (same file) with all of them; other editions aren't touched.
Missing source texts are downloaded into BibleSources first (the ones that can be: the others
come from BibleSources/input).
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bible_pages as bp  # noqa: E402

bs = bp.bs

# The other languages, in the order their rows appear.
OTHER_LANGUAGES = ["krv", "vietnamese", "thkjv", "martin", "luther1912"]
LANGUAGE_NAMES = {"krv": "Korean", "vietnamese": "Vietnamese", "thkjv": "Thai", "martin": "French",
                  "luther1912": "German"}


def has_source(version, book):
    return os.path.exists(bs.source_path(version, book))


def page_complete(path, labels):
    """Whether the page exists and has a column for every version in `labels`."""
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("| Hanzi"):
                cells = {c.strip() for c in line.strip().strip("|").split("|")}
                return all(label in cells for label in labels)
    return False


def add_common_arguments(p):
    p.add_argument("--languages", default=",".join(OTHER_LANGUAGES),
                   help="other languages' versions, comma-separated, in row order "
                        f"(default {','.join(OTHER_LANGUAGES)}: Korean, Vietnamese, Thai, French, German)")
    p.add_argument("--no-languages", action="store_true", help="no other languages")
    p.add_argument("--text-repo", default=bp.default_text_repo(), help="the ChineseReaderText folder")
    p.add_argument("--force", action="store_true", help="rebuild every page, even complete ones")
    p.add_argument("--dry-run", action="store_true", help="show what would be built, and stop")
    p.add_argument("--no-fetch", action="store_true", help="don't download missing source texts")


def run(args, *, testament, book_range, versions, edition, chapters_from):
    """Builds the pages: `versions` are the rows under the Chinese (original first)."""
    others = [] if args.no_languages else [v.strip() for v in args.languages.split(",") if v.strip()]
    versions = versions + [v for v in others if v not in versions]
    for version in versions:
        if version not in bs.VERSIONS:
            raise SystemExit(f"unknown version: {version}  (see: python3 bible/bible_pages.py --versions)")
    labels = [bs.VERSIONS[v]["label"] for v in versions]

    names = {bs.BOOKS[n - 1][0].lower(): n for n in book_range}
    books = []
    for name in args.books:
        if name.lower() not in names:
            raise SystemExit(f"Not in the {testament} Testament: {name}")
        books.append(names[name.lower()])
    books = books or list(book_range)
    folder = os.path.join(args.text_repo, "bible", "passages")
    if not os.path.isdir(folder):
        raise SystemExit(f"no bible/passages in {args.text_repo}: give --text-repo /path/to/ChineseReaderText")

    # 1. Source texts: download what BibleSources doesn't have yet.
    fetchable = [v for v in versions if bs.VERSIONS[v].get("fetch")]
    unfetchable_missing = sorted({(v, bs.BOOKS[b - 1][0]) for b in books for v in versions
                                  if not bs.VERSIONS[v].get("fetch") and not has_source(v, b)})
    for version, book in unfetchable_missing:
        print(f"  {version}: no {book} in BibleSources (it comes from input/, not a download)")
    missing = [b for b in books if not (all(has_source(v, b) for v in fetchable)
                                         and (has_source("cuv", b) or has_source("cut", b)))]
    if missing:
        fetch = os.path.join(bp.SOURCES_REPO, "common", "scripts", "bible_fetch.py")
        command = [sys.executable, fetch, *[bs.BOOKS[b - 1][0] for b in missing],
                   "--versions", ",".join(fetchable + ["cut"])]
        print(f"Source texts missing for {len(missing)} book(s):", ", ".join(bs.BOOKS[b - 1][0] for b in missing))
        if args.dry_run or args.no_fetch:
            print("  would run:", " ".join(f'"{c}"' if " " in c else c for c in command))
        else:
            subprocess.run(command, check=True)

    # 2. Which chapters need a page.
    plan = {}
    for book in books:
        if not has_source(chapters_from, book):
            print(f"  {bs.BOOKS[book - 1][0]}: every chapter, once its texts are downloaded"
                  if args.dry_run and not args.no_fetch else f"  {bs.BOOKS[book - 1][0]}: no {chapters_from} source yet, skipped")
            continue
        todo = []
        for chapter in sorted(int(c) for c in bs.load(chapters_from, book)["chapters"]):
            path = os.path.join(folder, f"{bs.book_slug(book)}-{chapter}.{edition}.md")
            if args.force or not page_complete(path, labels):
                todo.append((chapter, os.path.exists(path)))
        if todo:
            plan[book] = todo

    total = sum(len(t) for t in plan.values())
    rebuilt = sum(1 for t in plan.values() for _, exists in t if exists)
    print(f"{total} page(s) to build: {total - rebuilt} new, {rebuilt} rebuilt with the missing rows")
    print("Rows: simplified, pinyin, traditional, " + ", ".join(labels))
    for book, todo in plan.items():
        cs = [c for c, _ in todo]
        print(f"  {bs.BOOKS[book - 1][0]:16} {len(cs):3} chapter(s): {cs[0]}–{cs[-1]}" if len(cs) > 1
              else f"  {bs.BOOKS[book - 1][0]:16}   1 chapter: {cs[0]}")
    if args.dry_run or not plan:
        if not plan and not args.dry_run:
            print("Nothing to do: every chapter's page already has every row.")
        return

    # 3. Build, one book at a time (the Passages list is updated after each).
    pages = os.path.join(HERE, "scripture_pages.py")
    for book, todo in plan.items():
        name = bs.BOOKS[book - 1][0]
        refs = [f"{name} {c}" for c, _ in todo]
        print(f"\n{name}: {len(refs)} page(s)")
        subprocess.run([sys.executable, pages, *refs, "--with", ",".join(versions), "--edition", edition,
                        "--text-repo", args.text_repo], check=True)

    print(f"\nDone: {total} page(s) in {folder}\nReview with:  cd {args.text_repo} && git status")


def parser(doc):
    p = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("books", nargs="*", help="only these books (default: the whole testament)")
    return p
