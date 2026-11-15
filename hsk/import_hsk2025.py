#!/usr/bin/env python3
"""Imports the HSK 3.0 exam syllabus vocabulary (《HSK 考试大纲》, CLEC, November 2025) into
ChineseReaderText as word lists the app opens like the 2021 ones:
characters/data/hsk2025/hsk<level>-<from>-<to>.json, one file per 1,000 words.

Source: github.com/ofou/hsk (MIT), rebuilt from the official syllabus API (chinesetest.cn) and
checked band by band against the published 大纲: word, level, pinyin and part of speech, in
syllabus order. The syllabus gives no English or traditional forms; those come from the library's
other word lists (CC-CEDICT) where the word is the same, and traditional otherwise from OpenCC.

    python3 hsk/import_hsk2025.py            # download (or use hsk/data/hsk2025-vocabulary.csv) and write
    python3 hsk/import_hsk2025.py --report   # counts and words with no English, and stop
"""
import argparse
import csv
import glob
import json
import os
import re
import unicodedata
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_REPO = os.environ.get("CHINESEREADER_TEXT") or os.path.normpath(os.path.join(HERE, "..", "..", "ChineseReaderText"))
DATA = os.path.join(TEXT_REPO, "characters", "data")
OUT = os.path.join(DATA, "hsk2025")
CSV_URL = "https://github.com/ofou/hsk/releases/latest/download/vocabulary.csv"
CSV_CACHE = os.path.join(HERE, "data", "hsk2025-vocabulary.csv")
LEVELS = [("一级", "1"), ("二级", "2"), ("三级", "3"), ("四级", "4"), ("五级", "5"), ("六级", "6"), ("七-九级", "7–9")]
POS = {"名": "noun", "动": "verb", "形": "adjective", "副": "adverb", "代": "pronoun", "数": "numeral",
       "量": "measure word", "介": "preposition", "连": "conjunction", "助": "particle", "叹": "interjection",
       "拟声": "onomatopoeia", "数量": "numeral-measure", "前缀": "prefix", "后缀": "suffix"}


# Words CC-CEDICT doesn't have (or has without a usable definition): glossed by hand.
BY_HAND = {
    "新媒体": "new media", "新能源": "new energy; renewable energy sources", "占比": "proportion; share (of a total)",
    "精彩纷呈": "full of brilliant highlights", "居于": "to be located at; to occupy (a position)",
    "来之不易": "hard-won; not easily come by", "两翼": "the two wings; both flanks",
    "上半场": "first half (of a game or show)", "下半场": "second half (of a game or show)",
    "压轴": "the finale; to be the closing act", "不予": "not to grant; to refuse to (formal)",
    "致力于": "to devote oneself to; to be committed to",
}


def is_han(c):
    return "一" <= c <= "鿿" or "㐀" <= c <= "䶿"


def toneless(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("ü", "v").replace("u:", "v")


def syllable_set():
    from pypinyin.constants import PINYIN_DICT
    out = set()
    for value in PINYIN_DICT.values():
        for p in value.split(","):
            out.add(toneless(p))
    return out | {"r", "n", "ng", "m", "hm", "hng"}


SYLLABLES = None


def split_pinyin(pinyin, count):
    """'bàba', 2 → ['bà', 'ba']: the reading cut into `count` syllables (apostrophes and hyphens are breaks)."""
    global SYLLABLES
    SYLLABLES = SYLLABLES or syllable_set()
    parts = [p for p in re.split(r"[-'’ ]+", pinyin) if p]
    out = []
    for part in parts:
        n = len(part)
        # Fewest-syllables split of each part; the parts' counts must add up to `count`.
        best = {0: []}
        for i in range(1, n + 1):
            for j in range(max(0, i - 6), i):
                if j in best and toneless(part[j:i]) in SYLLABLES:
                    cand = best[j] + [part[j:i]]
                    if i not in best or len(cand) < len(best[i]):
                        best[i] = cand
        if n not in best:
            return None
        out += best[n]
    if len(out) != count:
        # Try the split with the most syllables when the fewest doesn't fit (e.g. xian → xi an).
        return None
    return out


CEDICT_FILE = os.path.join(HERE, "data", "cedict_1_0_ts_utf-8_mdbg.txt.gz")
TONE_MARKS = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "v": "ǖǘǚǜ"}


def marked(numbered):
    """'ke4' → 'kè', 'lu:4' → 'lǜ', 'qi5' → 'qi'."""
    m = re.fullmatch(r"([a-zA-Z:]+)([1-5])", numbered)
    if not m:
        return numbered.replace("u:", "ü")
    syl, tone = m.group(1).replace("u:", "v").replace("U:", "V"), int(m.group(2))
    if tone == 5:
        return syl.replace("v", "ü")
    low = syl.lower()
    if not any(v in low for v in "aeiouv"):
        return syl                                  # m, ng, r: no vowel to mark
    for vowel in ("a", "e"):
        if vowel in low:
            i = low.index(vowel)
            break
    else:
        i = low.index("o") if "ou" in low else max(low.rfind(v) for v in "aeiouv")
    out = syl[:i] + TONE_MARKS[low[i]][tone - 1] + syl[i + 1:]
    return out.replace("v", "ü")


def cedict():
    """Simplified → [(traditional, marked pinyin, definitions)] from CC-CEDICT."""
    import gzip
    path = CEDICT_FILE
    if not os.path.exists(path):
        try:
            import pycccedict
            path = os.path.join(os.path.dirname(pycccedict.__file__), "data", "cedict_1_0_ts_utf-8_mdbg.txt.gz")
        except ImportError:
            return {}
    out = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\S+) (\S+) \[([^\]]*)\] /(.*)/\s*$", line)
            if not m:
                continue
            trad, simp, pin, defs = m.groups()
            reading = "".join(marked(x) for x in pin.split())
            out.setdefault(simp, []).append((trad, reading, defs.split("/")))
    return out


def plain(defs):
    """Definitions with “surname …”, “variant of …” and cross-references put last."""
    weak = re.compile(r"^(surname |(old |archaic )?variant of|see |CL:|abbr\. for |used in )")
    good = [d for d in defs if d and not weak.match(d)]
    return good + [d for d in defs if d and weak.match(d)] if good else [d for d in defs if d]


def library_entries():
    """Simplified word → entries from the library's other lists (2021 HSK, words, characters)."""
    entries = {}
    files = sorted(glob.glob(os.path.join(DATA, "hsk*-*.json"))) + sorted(glob.glob(os.path.join(DATA, "words-*.json"))) \
        + sorted(glob.glob(os.path.join(DATA, "hanzi-*.json")))
    for f in files:
        for item in json.load(open(f, encoding="utf-8")).get("items", []):
            entries.setdefault(item["simplified"], item)
    return entries


def read_rows():
    if not os.path.exists(CSV_CACHE):
        os.makedirs(os.path.dirname(CSV_CACHE), exist_ok=True)
        req = urllib.request.Request(CSV_URL, headers={"User-Agent": "ChineseReaderTools"})
        with urllib.request.urlopen(req) as r, open(CSV_CACHE, "wb") as f:
            f.write(r.read())
    return list(csv.DictReader(open(CSV_CACHE, encoding="utf-8")))


def convert(rows):
    from opencc import OpenCC
    s2t = OpenCC("s2t")
    library = library_entries()
    dictionary = cedict()
    by_level = {code: [] for _, code in LEVELS}
    no_english, odd_pinyin = [], []
    for row in rows:
        level_zh = re.match(r"^([一二三四五六七八九\-]+级)", row["Level"]).group(1)
        code = dict(LEVELS)[level_zh]
        also = re.findall(r"（([一二三四五六七八九\-]+级)）", row["Level"])
        word = re.sub(r"\d+$", "", row["Word"])
        sense = re.search(r"(\d+)$", row["Word"])
        readings = [p.strip() for p in row["Pinyin"].split("/") if p.strip()]
        main = readings[0]
        chars = [c for c in word if is_han(c)]
        syllables = split_pinyin(main, len(chars))
        if syllables is None:
            odd_pinyin.append((word, main))
        known = library.get(word)
        meanings, english, traditional = [], "", None
        if known:
            traditional = known.get("traditional")
            wanted = toneless(main.replace("-", ""))
            same = [m for m in known.get("meanings", []) if toneless(m["pinyin"].replace(" ", "")) == wanted]
            others = [m for m in known.get("meanings", []) if m not in same]
            meanings = [dict(pinyin=main.replace("-", ""), definitions=m["definitions"]) for m in same] + others
            first = plain(same[0]["definitions"]) if same else []
            english = "; ".join(first[:3]) if first else ""
        lookup = word if word in dictionary or not word.endswith("儿") else word[:-1]   # 小偷儿 → 小偷
        if not english and lookup in dictionary:
            # CC-CEDICT: the entries read as the syllabus reads the word, else all of them.
            wanted = toneless(main.replace("-", "").removesuffix("r") if lookup != word else main.replace("-", ""))
            found = dictionary[lookup]
            same = [e for e in found if toneless(e[1]) == wanted] or found
            meanings = [dict(pinyin=e[1], definitions=plain(e[2])) for e in same] + meanings
            english = "; ".join(plain(same[0][2])[:3])
            traditional = traditional or [t + ("兒" if lookup != word else "")
                                          for t in sorted({e[0] for e in same}, key=lambda t: t != same[0][0])]
        if word in BY_HAND and (not english or not meanings):
            english = BY_HAND[word]
            meanings = [dict(pinyin=main.replace("-", ""), definitions=english.split("; "))] + meanings
        if not english:
            no_english.append(word)
        pos = [p.strip("（）()") for p in re.split(r"[、，,]", row["PartOfSpeech"]) if p.strip()]
        entry = {
            "rank": len(by_level[code]) + 1,
            "simplified": word,
            "traditional": traditional or [s2t.convert(word)],
            "pinyin": [r.replace("-", "") for r in readings],
            "english": english or ", ".join(POS.get(p, p) for p in pos),
            "meanings": meanings,
            "hsk": code,
            "syllables": syllables or [main.replace("-", "")],
            "syllabusNumber": int(row["No."]),
            "partOfSpeech": row["PartOfSpeech"],
        }
        if sense:
            entry["sense"] = int(sense.group(1))
        if also:
            entry["alsoAtLevels"] = [dict(LEVELS)[a] for a in also]
        by_level[code].append(entry)
    return by_level, no_english, odd_pinyin


def write(by_level):
    os.makedirs(OUT, exist_ok=True)
    written = []
    for _, code in LEVELS:
        items = by_level[code]
        name = "hsk" + code.replace("–", "-")
        for start in range(0, len(items), 1000):
            chunk = items[start:start + 1000]
            first, last = chunk[0]["rank"], chunk[-1]["rank"]
            path = os.path.join(OUT, f"{name}-{first:04d}-{last:04d}.json")
            data = {
                "kind": "words",
                "title": f"HSK {code} · 2025 · {first}–{last}",
                "description": f"HSK 3.0 exam syllabus (November 2025), level {code}: the {len(items)} words new at this "
                               "level, in syllabus order. English from CC-CEDICT where known; otherwise the part of speech.",
                "sources": ["《HSK 考试大纲》, Center for Language Education and Cooperation (CLEC), November 2025, "
                            "via github.com/ofou/hsk (MIT)", "English and traditional forms: CC-CEDICT, OpenCC"],
                "items": chunk,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
                f.write("\n")
            written.append((code, first, last, os.path.relpath(path, TEXT_REPO)))
    return written


def readme(written, counts):
    lines = ["## HSK-2025", "",
             "> The vocabulary of the HSK 3.0 exam syllabus (《HSK 考试大纲》, CLEC, November 2025), used by the "
             "HSK 1–6 exams from 13 December 2026: 300 · 500 · 1,000 · 2,000 · 3,600 · 5,400 · 11,000 words "
             "(cumulative). Each list has the words new at its level, in syllabus order.", ""]
    for zh, code in LEVELS:
        lines += [f"### HSK {code} · 第{zh}", ""]
        for c, first, last, path in written:
            if c == code:
                lines.append(f"- [HSK {code} · 2025 · {first}–{last} · 词汇 Vocabulary](../{path})")
        lines.append("")
    with open(os.path.join(TEXT_REPO, "hsk-2025", "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    rows = read_rows()
    by_level, no_english, odd = convert(rows)
    counts = {code: len(v) for code, v in by_level.items()}
    print("words per level:", counts, "total", sum(counts.values()))
    print(f"no English from the library: {len(no_english)}  ({' '.join(no_english[:30])} …)")
    print(f"pinyin not split into syllables: {len(odd)}  {odd[:12]}")
    if a.report:
        return
    written = write(by_level)
    readme(written, counts)
    print(f"wrote {len(written)} list file(s) to {os.path.relpath(OUT, TEXT_REPO)} and hsk-2025/README.md")


if __name__ == "__main__":
    main()
