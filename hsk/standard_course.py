#!/usr/bin/env python3
"""Lessons that follow the chapters of HSK Standard Course (HSK 标准教程, BLCU Press), in the same
format as the HSK 1–3 lessons. The words and grammar points follow the book's chapter; the
sentences and dialogs are new (the book's own texts aren't copied).

Sources: hsk/standard<book>/<chapter>.txt (same format as hsk_lessons.py; the chapter's English
title on a `title:` line, its Chinese title on a `zh:` line).

    python3 hsk/standard_course.py 2 4        # book 2, chapter 4 → hsk-standard/hsk2/04.md
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hsk_lessons as h  # noqa: E402

COURSE = "hsk-standard"


def build(book, chapter):
    path = os.path.join(h.HERE, f"standard{book}", f"{chapter:02d}.txt")
    meta = {}
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^(title|zh):\s*(.*)$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
    src = h.read_source(path)
    # Only the HSK 1–2 words and this chapter's are allowed.
    allowed = h.taught_before(3) | {w["word"] for w in src["words"]}
    problems = 0
    for block in src["words"] + src["grammar"] + src["dialogs"]:
        for zh, _ in block["lines"]:
            bad = [t for t in h.tokens_of(zh) if not h.allowed_token(t, allowed)]
            if bad:
                problems += 1
                print(f"not taught: {' '.join(bad)}  ← {zh}")
    py = h.Pinyin(3)
    title_zh = f"第{h.chinese_number(chapter)}课：{meta['zh']}"
    _, title_py = py.line(" ".join(h._segment(title_zh)))
    md = ["<!-- reader: speak=word -->",
          f"# {title_zh} | {title_py} | HSK Standard Course {book} · Lesson {chapter}: {meta['title']}", "",
          f"> **Draft** — new sentences and dialogs on the words and grammar of HSK 标准教程 {book}, "
          f"chapter {chapter}; not yet reviewed by a native speaker.", "",
          f"> **Goal:** {src['goal']}", "",
          f"## 生词 | Shēng cí | New words ({len(src['words'])})", "",
          "<!-- reader: table=glossary -->", "| Hanzi | Pinyin | English |", "|---|---|---|"]
    readings = [w["reading"] or " ".join(py.word(w["word"])) for w in src["words"]]
    for w, r in zip(src["words"], readings):
        md.append(f"| {w['word']} | {r} | {w['gloss']} |")
    md.append("")
    for i, (w, r) in enumerate(zip(src["words"], readings), 1):
        md += [f"## 生词{i}：{w['word']} | Shēng cí {i} : {r} | Word {i}: {r} — {w['gloss']}", ""]
        md += h._table(w["lines"], py)
    for g in src["grammar"]:
        _, head_py = py.line(" ".join(h._segment(g["head"])))
        md += [f"## 语法：{g['head']} | Yǔ fǎ : {head_py[:1].lower() + head_py[1:]} | Grammar: {g['title']}", ""]
        md += [x for note in g["note"] for x in (f"> {note}", "")]
        if g["lines"]:
            md += h._table(g["lines"], py)
    for i, d in enumerate(src["dialogs"], 1):
        md += [f"## 对话{h.chinese_number(i)} | Duì huà {py.word(h.chinese_number(i))[0]} | Dialog {i} · {d['title']}", ""]
        md += h._table(d["lines"], py, dialog=True)
    out_dir = os.path.join(h.TEXT_REPO, COURSE, f"hsk{book}")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{chapter:02d}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md).rstrip() + "\n")
    index(book, chapter, title_zh, meta["title"])
    print(f"built {COURSE}/hsk{book}/{chapter:02d}.md ({problems} vocabulary problem(s))")
    if py.new:
        print("Readings from pypinyin — look these over: " + "  ".join(f"{w} {' '.join(py.lazy(w))}" for w in sorted(py.new)))


def index(book, chapter, title_zh, title_en):
    """The course's list (hsk-standard/README.md) and its entry in catalog.md."""
    readme = os.path.join(h.TEXT_REPO, COURSE, "README.md")
    text = open(readme, encoding="utf-8").read() if os.path.exists(readme) else \
        "## HSK 标准教程 · HSK Standard Course\n\n" \
        "<!-- Lessons on the chapters of HSK Standard Course (BLCU Press): the chapter's words and grammar,\n" \
        "with new sentences and dialogs. One ### heading per book. -->\n"
    heading = f"### HSK 标准教程 {book} · Standard Course {book}"
    line = f"- [{title_zh} · {title_en}](hsk{book}/{chapter:02d}.md)"
    if heading not in text:
        text = text.rstrip("\n") + f"\n\n{heading}\n\n"
    if line not in text:
        part = text.split(heading)
        lines = [l for l in part[1].strip("\n").split("\n") if l.startswith("- [")] + [line]
        lines.sort(key=lambda l: re.search(r"\((hsk\d+/\d+)\.md\)", l).group(1))
        rest = re.sub(r"\A(\n*- \[.*\n?)*", "", part[1].lstrip("\n"))
        text = part[0] + heading + "\n\n" + "\n".join(lines) + "\n" + ("\n" + rest if rest.strip() else "")
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    catalog = os.path.join(h.TEXT_REPO, "catalog.md")
    cat = open(catalog, encoding="utf-8").read()
    if f"## {COURSE} ·" not in cat:
        entry = (f"## {COURSE} · HSK 标准教程 Standard Course\n- index: [{COURSE}/README.md]({COURSE}/README.md)\n"
                 "- Lessons on the chapters of HSK Standard Course (HSK 2.0 textbooks): each chapter's words and "
                 "grammar with new sentences and dialogs.\n")
        cat = cat.replace("## hsk-2025 ·", entry + "\n## hsk-2025 ·", 1)
        with open(catalog, "w", encoding="utf-8") as f:
            f.write(cat)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("book", type=int)
    p.add_argument("chapter", type=int)
    a = p.parse_args()
    build(a.book, a.chapter)


if __name__ == "__main__":
    main()
