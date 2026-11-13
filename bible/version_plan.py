#!/usr/bin/env python3
"""For version_branches.sh: which versions to turn into passage editions, and for which passages.
Prints one tab-separated line per version:

    key  edition  lang  option  branch  label  license  passages(;)

  option   --en (an English version) or --study (Korean, Thai and other study languages)
  edition  the edition name (file romans-12.<edition>.md): the key, without "-input"

Only versions that may be published go in (public domain or Creative Commons) unless
--include-restricted. Duplicates are left out: "kjv-input" when "kjv" has the books, and
versions an existing edition already shows (web: Study; bbe: Basic English).
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bible_pages as bp  # noqa: E402  (finds BibleSources; gives VERSIONS and bible_sources)

bs = bp.bs
SAME_AS_EDITION = {"web", "bbe", "basicenglish"}          # already the English of Study / Basic English
SAME_TEXT = {"korean": "krv", "thai": "thkjv"}            # other copies of a version we have

PUBLISHABLE = re.compile(r"^(public domain|cc by)", re.I)


def publishable(key):
    return bool(PUBLISHABLE.match(bs.VERSIONS[key].get("license", "Public domain")))


def passages(text_repo):
    """The passages ChineseReaderText already has (their default-edition pages): [(book, ref text)]."""
    folder = os.path.join(text_repo, "bible", "passages")
    slugs = {bs.book_slug(n): n for n in range(1, 67)}
    found = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        m = re.fullmatch(r"(.+?)-(\d+)(?:-(\d+)(?:-(\d+))?)?\.md", name)
        if not m or m[1] not in slugs:
            continue
        book = slugs[m[1]]
        ref = f"{bs.BOOKS[book - 1][0]} {m[2]}" + (f":{m[3]}" + (f"-{m[4]}" if m[4] else "") if m[3] else "")
        found.append((book, ref))
    return found


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lang", default="en,ko,th")
    p.add_argument("--versions", default="")
    p.add_argument("--include-restricted", action="store_true")
    p.add_argument("--text-repo", default=bp.default_text_repo())
    args = p.parse_args()

    langs = [l.strip() for l in args.lang.split(",") if l.strip()]
    named = [v.strip() for v in args.versions.split(",") if v.strip()]
    for key in named:
        if key not in bs.VERSIONS:
            sys.exit(f"unknown version: {key}")
    refs = passages(args.text_repo)
    if not refs:
        sys.exit(f"no passages in {args.text_repo}/bible/passages")

    for key, v in bs.VERSIONS.items():
        if named and key not in named:
            continue
        if not named:
            if v["lang"] not in langs or not bs.available_books(key):
                continue
            base = key[:-len("-input")] if key.endswith("-input") else None
            if base and bs.available_books(base):
                continue
            if key in SAME_AS_EDITION or (key in SAME_TEXT and bs.available_books(SAME_TEXT[key])):
                continue
        restricted = not publishable(key)
        if restricted and not args.include_restricted:
            print(f"#skip\t{key}\t{v.get('license', '')}")
            continue
        # The passages this version (and the base edition's own sources) can make.
        edition = {**bp.load_editions()[1][bp.load_editions()[0]]}
        option = "--en" if v["lang"] == "en" else "--study"
        edition["en" if option == "--en" else "study"] = key
        usable = [ref for book, ref in refs
                  if all(os.path.exists(bs.source_path(n, book)) for n in bp.needed_sources(book, edition))]
        if not usable:
            print(f"#skip\t{key}\tnone of the passages' books")
            continue
        name = base_name = key[:-len("-input")] if key.endswith("-input") else key
        branch = f"version/{v['lang']}/{base_name}"
        print("\t".join([key, name, v["lang"], option, branch, v["label"],
                         v.get("license", "Public domain"), ";".join(usable)]))


if __name__ == "__main__":
    main()
