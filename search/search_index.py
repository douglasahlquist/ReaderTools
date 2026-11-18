#!/usr/bin/env python3
"""Builds the search files the reader app downloads for 🔍 Search: one file per version, one
line per verse, so the whole Bible or Qur'an can be searched in a version without opening its
pages.

    ChineseReaderText/search/index.json        the versions, their files, verse counts
    ChineseReaderText/search/<version>.tsv     <page key> TAB <verse> TAB <text>

Page keys are the passage file names without edition: "genesis-1" (bible/passages/genesis-1.wlc.md),
"001-al-fatihah" (islam/quran/001-al-fatihah.md). Versions are matched to their table columns by
bible/versions.json (Hanzi → simplified, Pinyin → pinyin, 繁體 → traditional, a version's labels →
that version; the original-language labels WLC, SBLGNT … all go to "original").

    python3 search_index.py [--library ~/Documents/workspace_chinese/ChineseReaderText]
"""
import argparse
import glob
import json
import os
import re

HOME = os.path.expanduser("~")
DEFAULT_LIBRARY = os.path.join(HOME, "Documents/workspace_chinese/ChineseReaderText")
COLLECTIONS = [("bible", "bible/passages/*.md"), ("quran", "islam/quran/*.md")]


def cells(line):
    t = line.strip()
    if t.startswith("|"):
        t = t[1:]
    if t.endswith("|"):
        t = t[:-1]
    # "\|" inside a cell is a literal bar.
    parts = re.split(r"(?<!\\)\|", t)
    return [p.strip().replace("\\|", "|") for p in parts]


def split_number(cell):
    m = re.match(r"^(\d+)(?:\s+(.*))?$", cell.strip())
    return (m.group(1), (m.group(2) or "").strip()) if m else (None, cell.strip())


def is_separator(row):
    return all(c and set(c) <= set("-:") for c in row)


def page_key(path):
    return os.path.basename(path).split(".")[0]


def verse_rows(text):
    """(labels, row) for every row of every verses table in a page; labels name each cell."""
    pending = False
    labels = None
    for line in text.splitlines():
        if "reader: table=verses" in line:
            pending, labels = True, None
            continue
        if not line.strip().startswith("|"):
            if labels is not None and line.strip():
                pending, labels = False, None
            continue
        if not pending:
            continue
        row = cells(line)
        if labels is None:
            labels = row
            continue
        if is_separator(row):
            continue
        yield labels, row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", default=DEFAULT_LIBRARY)
    args = ap.parse_args()
    lib = args.library

    catalog = json.load(open(os.path.join(lib, "bible/versions.json"), encoding="utf-8"))["versions"]
    by_label = {"Hanzi": "simplified", "Pinyin": "pinyin", "繁體": "traditional", "简体": "simplified"}
    for v in catalog:
        if v["kind"] in ("original", "translation"):
            for label in v.get("labels") or []:
                by_label[label] = v["id"]

    verses = {}       # version id → {(key, verse): text}
    collection_of = {}
    pages = 0
    for collection, pattern in COLLECTIONS:
        # A chapter's several page files (editions) carry the same verses: the first one wins.
        # The traditional-first editions (.chinese-trad.md) come last, so "Hanzi" stays simplified.
        files = sorted(glob.glob(os.path.join(lib, pattern)), key=lambda p: (".chinese-trad." in p, p))
        for path in files:
            key = page_key(path)
            pages += 1
            for labels, row in verse_rows(open(path, encoding="utf-8").read()):
                number, _ = split_number(row[0]) if row else (None, "")
                if number is None:
                    continue
                for index, cell in enumerate(row):
                    if index >= len(labels):
                        break
                    version = by_label.get(labels[index])
                    if not version:
                        continue
                    n, text = split_number(cell)
                    text = text if n == number else cell.strip()
                    if not text:
                        continue
                    if version in ("simplified", "traditional"):
                        text = text.replace(" ", "")          # the words are spaced for tapping
                    store = verses.setdefault(version, {})
                    store.setdefault((key, int(number)), text)
                    collection_of[version] = collection

    out = os.path.join(lib, "search")
    os.makedirs(out, exist_ok=True)
    index = {"versions": []}
    for version, rows in sorted(verses.items()):
        name = f"{version}.tsv"
        order = {}
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            for (key, verse), text in sorted(rows.items(), key=lambda kv: (kv[0][0], kv[0][1])):
                f.write(f"{key}\t{verse}\t{text.replace(chr(9), ' ')}\n")
        size = os.path.getsize(os.path.join(out, name))
        index["versions"].append({"id": version, "collection": collection_of[version], "file": name,
                                  "verses": len(rows), "bytes": size})
        print(f"{version:22} {collection_of[version]:6} {len(rows):6} verses {size / 1e6:6.1f} MB")
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{pages} pages → {out}")


if __name__ == "__main__":
    main()
