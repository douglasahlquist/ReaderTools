#!/usr/bin/env python3
"""Egyptian Glyphs for ChineseReaderText: Gardiner's list of hieroglyphic signs, one page per
group (A Man and his occupations … Aa Unclassified), each sign with its Gardiner code, a
description and how it's used (determinative, ideogram, phonogram). From gardiner_signs.tsv
(made from "Alan Gardiner's List of Hieroglyphic Signs"). Writes ChineseReaderText/egyptian/
(README.md, 00.md and a page per group) and the section's entry in catalog.md.

The hieroglyphs are Unicode characters (U+13000–U+1342F): the app shows them with a
hieroglyph font.

    python3 egyptian/egyptian_pages.py
    python3 egyptian/egyptian_pages.py --text-repo ~/Documents/workspace_chinese/ChineseReaderText
"""
import argparse
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SECTION_ID = "egyptian-glyphs"
TITLE = "𓂀 Egyptian Glyphs"


def load(tsv):
    groups = []
    with open(tsv, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if not groups or groups[-1]["letter"] != row["group"]:
                groups.append({"letter": row["group"], "title": row["group_title"], "signs": []})
            groups[-1]["signs"].append(row)
    return groups


def cell(text):
    return text.replace("|", "\\|").strip()


def title_case(text):
    small = {"and", "of", "the", "etc."}
    words = text.lower().split()
    return " ".join(w if (i and w in small) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def slug(group):
    """The group's page: its letter ("a.md", "aa.md")."""
    return f"{group['letter'].lower()}.md"


def page(group):
    title = f"{group['letter']}. {title_case(group['title'])}"
    first = group["signs"][0]["glyph"]
    lines = ["<!-- reader: lang=en-US -->", "", f"# {first} | {group['letter']} | {title}", "",
             "<!-- reader: table=glossary -->", "| Name | Romanization | English |", "|---|---|---|"]
    for sign in group["signs"]:
        text = sign["description"] or "—"
        if sign["details"]:
            text += " · " + sign["details"]
        lines.append(f"| {sign['glyph']} | {sign['code']} | {cell(text)} |")
    return "\n".join(lines) + "\n"


ABOUT = """<!-- reader: lang=en-US -->

# 𓂀 | | Egyptian Glyphs

> The signs of Egyptian hieroglyphic writing, as Sir Alan Gardiner listed them in his *Egyptian Grammar* (1927): **{count} signs in {groups} groups**, from A (a man and his occupations) to Aa (unclassified). Each sign has its Gardiner code (A1, G17 …), what it shows, and how it's used.

> **Det.** a determinative: written after a word to show what kind of word it is (a seated man after a man's name). **Ideo.** an ideogram: the sign stands for the word itself. **Phono.** a phonogram: the sign stands for its sounds (ꜣ, nfr …).

> Source: "Alan Gardiner's List of Hieroglyphic Signs". The hieroglyphs are Unicode characters.
"""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tsv", default=os.path.join(HERE, "gardiner_signs.tsv"))
    p.add_argument("--text-repo", default=os.path.join(HERE, "..", "..", "ChineseReaderText"))
    a = p.parse_args()
    groups = load(a.tsv)
    count = sum(len(g["signs"]) for g in groups)
    out = os.path.join(a.text_repo, "egyptian")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "00.md"), "w", encoding="utf-8") as f:
        f.write(ABOUT.format(count=count, groups=len(groups)))
    index = [f"## {TITLE}", "", "### Gardiner's Sign List", "", "- [About the glyphs](00.md)"]
    for group in groups:
        name = slug(group)
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(page(group))
        index.append(f"- [{group['signs'][0]['glyph']} {group['letter']} · {title_case(group['title'])} "
                     f"({len(group['signs'])})]({name})")
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index) + "\n")
    # The section in the catalog (＋ in the app), once.
    catalog = os.path.join(a.text_repo, "catalog.md")
    text = open(catalog, encoding="utf-8").read()
    if f"## {SECTION_ID} ·" not in text:
        entry = (f"## {SECTION_ID} · {TITLE}\n- index: [egyptian/README.md](egyptian/README.md)\n"
                 f"- Gardiner's list of hieroglyphic signs: {count} signs in {len(groups)} groups, "
                 "each with its code, what it shows and how it's used.\n\n")
        text = re.sub(r"(?=## music ·)", lambda _: entry, text, count=1) if "## music ·" in text else text + "\n" + entry
        with open(catalog, "w", encoding="utf-8") as f:
            f.write(text)
    print(f"wrote egyptian/: {len(groups)} group pages, {count} signs; catalog entry {SECTION_ID}")


if __name__ == "__main__":
    main()
