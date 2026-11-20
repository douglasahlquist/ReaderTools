#!/usr/bin/env python3
"""Bring the combined passage pages (bible/passages/*.md) in line with the version folders, until
the app reads versions/ directly and the pages can go.

For every verse table on every page, each column whose label is a known version is rewritten from
versions/<key>/: the WLC through the Masoretic map, so Hebrew verses sit beside the right English
verse. A whole-chapter page (<book>-<n>.wlc.md / .kjv.md) also gets the rows it was missing (John 7:53),
with its group heading's range updated, and Malachi 4 gets a page and an entry in bible/README.md.

A verse a version lacks shows, in that version's cell only:
  (omitted in this edition — <reason>)        listed in coverage.omitted / notes
  (missing — possibly a data error)            inside coverage, not explained
  (nothing)                                    outside the version's coverage or beyond the KJV numbering

  python3 patch_pages.py ~/Documents/workspace_chinese/ReaderText [--dry-run]
"""
import argparse, json, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_versions import BOOKS

SLUG = {s: (u, name) for s, u, name, _ in BOOKS}
# column label → (version key, part): part is text, pinyin or the Chinese cells (numbered)
LABELS = {"繁體": "zh-cuv-t", "简体": "zh-cuv-s", "WLC": "hbo-wlc", "SBLGNT": "grc-sblgnt", "TR": "grc-tr",
          "KJV": "en-kjv", "WEB": "en-web", "BBE": "en-bbe", "개역한글": "ko-krv", "Vietnamese (1934)": "vi-1934",
          "ThaiKJV": "th-kjv", "Martin (1744)": "fr-martin", "Luther (1912)": "de-luther1912", "Naskapi": "nsk-naskapi"}
JOINED_ZH = {"s": "（并入下节）", "t": "（併入下節）", "p": "( bìng rù xià jié )"}

class Library:
    def __init__(self, lib):
        self.root = f"{lib}/versions/bible"; self.meta = {}; self.cache = {}
        self.kjv = json.load(open(f"{lib}/schemes/kjv.json"))["books"]
        self.maso = json.load(open(f"{lib}/schemes/masoretic.json"))["fromKJV"]
        for key in os.listdir(self.root):
            p = f"{self.root}/{key}/version.json"
            if os.path.exists(p): self.meta[key] = json.load(open(p, encoding="utf-8"))

    def chapter(self, key, book, ch):
        k = (key, book, ch)
        if k not in self.cache:
            rows = {}
            p = f"{self.root}/{key}/{book}/{ch}.tsv"
            if os.path.exists(p):
                for line in open(p, encoding="utf-8"):
                    r = line.rstrip("\n").split("\t"); rows[r[0]] = r
            self.cache[k] = rows
        return self.cache[k]

    def verse(self, key, book, ch, v):
        """the version's row for a KJV-numbered verse (the WLC through the Masoretic map)"""
        if self.meta.get(key, {}).get("numbering") == "masoretic":
            b, c, vv = self.maso.get(f"{book}.{ch}.{v}", f"{book}.{ch}.{v}").split(".")
            return self.chapter(key, b, int(c)).get(vv)
        return self.chapter(key, book, ch).get(str(v))

    def notice(self, key, book, ch, v):
        """what to show where the version has no text for this verse"""
        cov = self.meta.get(key, {}).get("coverage", {})
        books = cov.get("books", {})
        if book not in books: return ""
        if books[book] != "all":
            chs = set()
            for part in books[book].split(","):
                a, _, b = part.partition("-"); chs.update(range(int(a), int(b or a) + 1))
            if ch not in chs: return ""
        n = self.kjv.get(book, [])
        if ch > len(n) or not str(v).isdigit() or int(v) > n[ch - 1]: return ""
        ref = f"{book}.{ch}.{v}"
        if ref in cov.get("omitted", []):
            why = cov.get("notes", {}).get(ref, "")
            return f"(omitted in this edition{' — ' + why if why else ''})"
        return "(missing — possibly a data error)"

def cell(text): return text.replace("|", "／").strip()

def split_row(line): return [c.strip() for c in line.strip().strip("|").split("|")]

def verse_num(cellv):
    m = re.match(r"(\d+)\s", cellv + " "); return m[1] if m else None

def build_row(lib, header, book, ch, v, old=None, chinese=True):
    """cells for verse v under `header`; old cells kept for columns this tool doesn't know"""
    trad_first = "简体" in header                      # a traditional-first edition page
    zh_main = "zh-cuv-t" if trad_first else "zh-cuv-s"
    cells = []
    for i, label in enumerate(header):
        if label in ("Hanzi", "Pinyin") or LABELS.get(label, "").startswith("zh-cuv"):
            if not chinese and old:                    # edition pages keep their own Chinese text
                cells.append(old[i] if i < len(old) else ""); continue
            key = zh_main if label in ("Hanzi", "Pinyin") else LABELS[label]
            row = lib.verse(key, book, ch, v)
            if row: txt = row[2] if label == "Pinyin" else row[1]
            else:
                joined = f"{book}.{ch}.{v}" in lib.meta[key]["coverage"].get("omitted", [])
                part = "p" if label == "Pinyin" else ("t" if key == "zh-cuv-t" else "s")
                txt = JOINED_ZH[part] if joined else ""
            cells.append(f"{v} {cell(txt)}".strip() if txt else (f"{v}" if label == "Hanzi" else ""))
        elif label in LABELS:
            key = LABELS[label]
            if key not in lib.meta: cells.append(old[i] if old and i < len(old) else ""); continue
            row = lib.verse(key, book, ch, v)
            cells.append(cell(row[1]) if row else lib.notice(key, book, ch, v))
        else:
            cells.append(old[i] if old and i < len(old) else "")
    return "| " + " | ".join(cells) + " |"

def heading(a, b):
    return (f"## 第{a}–{b}节 | Dì {a}–{b} jié | Verses {a}–{b}" if a != b else
            f"## 第{a}节 | Dì {a} jié | Verse {a}")

def patch(lib, path, book, ch, whole):
    """whole: a whole-chapter page (.wlc / .kjv), whose rows are completed and whose Chinese is rewritten."""
    lines = open(path, encoding="utf-8").read().split("\n")
    out, changed, i = [], False, 0
    tables = []                                       # (heading index in out, [row indexes in out], header)
    head_idx = None; header = None; rows_idx = None
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "): head_idx = len(out)
        if line.strip() == "<!-- reader: table=verses -->" and i + 2 < len(lines):
            header = split_row(lines[i + 1]); out += [line, lines[i + 1], lines[i + 2]]; i += 3
            rows_idx = []; tables.append((head_idx, rows_idx, header))
            while i < len(lines) and lines[i].startswith("|"):
                old = split_row(lines[i]); v = verse_num(old[0]) if old else None
                new = build_row(lib, header, book, ch, v, old, chinese=whole) if v else lines[i]
                changed |= new != lines[i]; rows_idx.append((len(out), v)); out.append(new); i += 1
            continue
        out.append(line); i += 1
    if whole and tables:
        have = {v for _, rows, _ in tables for _, v in rows if v}
        want = set(str(x) for x in range(1, lib.kjv[book][ch - 1] + 1)) if ch <= len(lib.kjv.get(book, [])) else set()
        for v in sorted(want - have, key=int):
            # the table holding verse v-1 (or the first)
            t = next((t for t in tables if any(x == str(int(v) - 1) for _, x in t[1])), tables[0])
            h, rows, header = t
            after = max((idx for idx, x in rows if x and int(x) < int(v)), default=rows[0][0] - 1 if rows else None)
            new = build_row(lib, header, book, ch, v)
            out.insert(after + 1, new)
            # shift every recorded index after the insertion point
            for tt in tables:
                tt[1][:] = [(idx + 1 if idx > after else idx, x) for idx, x in tt[1]]
            tables = [(hh + 1 if hh is not None and hh > after else hh, r, hd) for hh, r, hd in tables]
            t = next(tt for tt in tables if tt[1] is rows)
            rows.append((after + 1, v)); rows.sort()
            nums = [int(x) for _, x in rows if x]
            if t[0] is not None and re.match(r"## 第", out[t[0]]): out[t[0]] = heading(min(nums), max(nums))
            changed = True
    if changed: open(path, "w", encoding="utf-8").write("\n".join(out))
    return changed

def malachi_4(lib, folder, readme):
    src, dst = f"{folder}/malachi-3.wlc.md", f"{folder}/malachi-4.wlc.md"
    lines = open(src, encoding="utf-8").read().split("\n")
    first_table = next(i for i, l in enumerate(lines) if l.strip() == "<!-- reader: table=verses -->")
    header = split_row(lines[first_table + 1])
    title = [l.replace(" 3 |", " 4 |").replace("Malachi 3", "Malachi 4") if l.startswith("# ") else l
             for l in lines[:next(i for i, l in enumerate(lines) if l.startswith("## "))]]
    end = max(i for i, l in enumerate(lines) if l.startswith("|"))
    tail = lines[end + 1:]
    body = [heading(1, 6), "", "<!-- reader: table=verses -->", lines[first_table + 1], lines[first_table + 2]]
    body += [build_row(lib, header, "MAL", 4, str(v)) for v in range(1, 7)]
    open(dst, "w", encoding="utf-8").write("\n".join(title + body + tail))
    text = open(readme, encoding="utf-8").read()
    if "passages/malachi-4" not in text:
        text = text.replace("- [3](passages/malachi-3.wlc.md)", "- [3](passages/malachi-3.wlc.md)\n- [4](passages/malachi-4.wlc.md)")
        open(readme, "w", encoding="utf-8").write(text)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("library"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(); lib_dir = os.path.expanduser(a.library)
    lib = Library(lib_dir); folder = f"{lib_dir}/bible/passages"
    if not a.dry_run: malachi_4(lib, folder, f"{lib_dir}/bible/README.md")
    count = 0
    for f in sorted(os.listdir(folder)):
        m = re.match(r"(.+)-(\d+)(?:\.([a-z0-9-]+))?\.md$", f)
        if not m or m[1] not in SLUG: continue
        whole = m[3] in ("wlc", "kjv")
        if a.dry_run: continue
        count += patch(lib, f"{folder}/{f}", SLUG[m[1]][0], int(m[2]), whole)
    print(f"{count} page(s) changed")

if __name__ == "__main__":
    main()
