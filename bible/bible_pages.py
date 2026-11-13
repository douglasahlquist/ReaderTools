#!/usr/bin/env python3
"""Builds Chinese Reader pages for Bible passages from the texts in ChineseReaderTools/sources/
(fetch them first with bible_fetch.py). Each verse shows the Hanzi with its pinyin, then the
Greek or Hebrew, then the English, then any other versions, one row each.

    python3 bible/bible_pages.py "Romans 12"                    # the default edition (editions.json)
    python3 bible/bible_pages.py Romans                         # every chapter: romans-1.md … romans-16.md
    python3 bible/bible_pages.py "Romans 12-14" "Psalm 23"
    python3 bible/bible_pages.py "John 3:16" "Romans 8:28-39"   # verses
    python3 bible/bible_pages.py "Romans 12" --edition classic  # another edition: romans-12.classic.md
    python3 bible/bible_pages.py "Romans 12" --edition study,classic,basic
    python3 bible/bible_pages.py "Romans 12" --all-editions
    python3 bible/bible_pages.py "Romans 12" --en web,kjv --as compare   # a one-off edition
    python3 bible/bible_pages.py --index-only                   # just rebuild the 经文 Passages list
    python3 bible/bible_pages.py --editions                     # the editions and their versions

Editions are named sets of versions in bible/editions.json. Pages go to bible/passages/ in
ChineseReaderText (beside ChineseReaderTools; --text-repo or $CHINESEREADER_TEXT to point
elsewhere): romans-12.md for the default edition, romans-12.classic.md for another; verses as
john-3-16.md and romans-8-28-39.md (no “:” in file names). Each run rebuilds the 经文 Passages
list in bible/README.md, one line per passage with a link to each of its editions; the app
lists the passage once and switches editions on the page.

Your own text: --hanzi-file and --english-file take one verse per line (“16 text” or “3:16 text”)
and replace those verses. Pinyin always comes from the Hanzi.

Needs: pip3 install -r requirements.txt   (pypinyin, jieba, opencc-python-reimplemented)
"""
import argparse
import json
import os
import re
import sys
import unicodedata


def _sources_repo():
    """BibleSources (the source texts and bible_sources.py): from BIBLE_SOURCES_REPO, or in
    ~/Documents/workspace_bible_sources/BibleSources."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [os.environ.get("BIBLE_SOURCES_REPO"),
                  os.path.join(here, "..", "..", "..", "workspace_bible_sources", "BibleSources"),
                  os.path.expanduser("~/Documents/workspace_bible_sources/BibleSources")]
    for path in candidates:
        if path and os.path.exists(os.path.join(path, "common", "scripts", "bible_sources.py")):
            return os.path.normpath(path)
    sys.exit("Can't find BibleSources (common/scripts/bible_sources.py). It belongs in "
             "~/Documents/workspace_bible_sources/BibleSources, or set BIBLE_SOURCES_REPO.")


# This folder (ChineseReaderTools/bible): editions.json, and the way to ChineseReaderText.
TOOLS_BIBLE = os.path.dirname(os.path.abspath(__file__))
SOURCES_REPO = _sources_repo()
sys.path.insert(0, os.path.join(SOURCES_REPO, "common", "scripts"))
import bible_sources as bs  # noqa: E402
from bible_sources import BOOKS, NT_START, VERSIONS, to_simplified, to_traditional  # noqa: E402

try:
    from pypinyin import Style, lazy_pinyin, load_phrases_dict
    import jieba
    HAVE_PINYIN = True
except ImportError:                     # --index-only and --versions work without them
    HAVE_PINYIN = False

    def load_phrases_dict(_phrases):
        pass

    class _NoJieba:
        def __getattr__(self, _name):
            return lambda *a, **k: None
    jieba = _NoJieba()

jieba.setLogLevel(60)
# Bible words the segmenter should keep whole, and splits it gets wrong in the CUV.
for _w in ["果子", "服事", "恒切", "圣徒", "帮补", "同心", "俯就", "牧者", "安歇", "以恶报恶", "神", "主", "得着",
           "弟兄们", "慈悲", "察验", "纯全", "旨意", "肢体", "恩赐", "预言", "执事", "教导", "劝化", "施舍"]:
    jieba.add_word(_w)
jieba.suggest_freq(("结", "果子"), True)               # 结果子 “bear fruit”, not 结果 “result”
for _w in ["事主", "中要", "要恒切", "我必", "我以", "爱人", "神爱世人", "当照", "美的", "事要", "倒要", "神爱", "神所"]:
    jieba.del_word(_w)

# ------------------------------------------------------------------------------------ pinyin
# Readings that pypinyin gets wrong in the Bible, and names it doesn't know.
PHRASES = {
    "耶稣": [["yē"], ["sū"]], "耶和华": [["yē"], ["hé"], ["huá"]], "弟兄": [["dì"], ["xiong"]],
    "弟兄们": [["dì"], ["xiong"], ["men"]], "祭": [["jì"]], "献祭": [["xiàn"], ["jì"]],
    "圣灵": [["shèng"], ["líng"]], "以色列": [["yǐ"], ["sè"], ["liè"]], "基督": [["jī"], ["dū"]],
    "行善": [["xíng"], ["shàn"]], "行恶": [["xíng"], ["è"]], "恶": [["è"]], "为善": [["wéi"], ["shàn"]],
    "喜乐": [["xǐ"], ["lè"]], "乐意": [["lè"], ["yì"]], "长久": [["cháng"], ["jiǔ"]],
    "得着": [["dé"], ["zháo"]], "着": [["zhe"]], "仇敌": [["chóu"], ["dí"]], "报应": [["bào"], ["yìng"]],
    "伸冤": [["shēn"], ["yuān"]], "炭火": [["tàn"], ["huǒ"]], "供给": [["gōng"], ["jǐ"]],
    "看守": [["kān"], ["shǒu"]], "长老": [["zhǎng"], ["lǎo"]], "传道": [["chuán"], ["dào"]],
    "所得": [["suǒ"], ["dé"]], "用处": [["yòng"], ["chu"]], "照着": [["zhào"], ["zhe"]],
    "凭着": [["píng"], ["zhe"]], "服事": [["fú"], ["shi"]], "事奉": [["shì"], ["fèng"]],
    "时候": [["shí"], ["hou"]], "果子": [["guǒ"], ["zi"]],
}
# One-character words read differently on their own than pypinyin's default.
SINGLE = {"得": "de", "着": "zhe", "了": "le", "地": "dì"}
# 得 is dé (“to get”) after these words, de (linking a verb to how it's done) otherwise.
DE_GET = {"反", "必", "可", "就", "才", "能", "要", "已", "不", "未", "所", "便", "要", "得以", "也", "都", "又"}
OPENING = set("「『“‘（(《")
# 为 is wéi (“to be, to become”) after these words: 便为有福, 乃为, 成为 …
WEI_AFTER = {"便", "乃", "成", "称", "就", "即", "必"}
load_phrases_dict(PHRASES)

PUNCT = {"，": ",", "。": ".", "；": ";", "：": ":", "？": "?", "！": "!", "、": ",",
         "「": "“", "」": "”", "『": "‘", "』": "’", "（": "(", "）": ")"}
SENTENCE_END = set("。？！")


def is_han(ch):
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


def sandhi(syllables, chars):
    """不 bù → bú and 一 yī → yí / yì before the next syllable's tone, as spoken."""
    def tone(s):
        for c in unicodedata.normalize("NFD", s):
            if c in "̄́̌̀":
                return {"̄": 1, "́": 2, "̌": 3, "̀": 4}[c]
        return 5
    out = list(syllables)
    for i, ch in enumerate(chars[:-1]):
        nxt = tone(syllables[i + 1]) if i + 1 < len(syllables) else 5
        if ch == "不" and out[i] == "bù" and nxt == 4:
            out[i] = "bú"
        elif ch == "一" and out[i] == "yī" and not is_han_number(chars, i):
            out[i] = "yí" if nxt == 4 else "yì" if nxt in (1, 2, 3) else "yī"
    return out


def is_han_number(chars, i):
    numerals = set("〇一二三四五六七八九十百千万")
    return (i > 0 and chars[i - 1] in numerals | {"第"}) or (i + 1 < len(chars) and chars[i + 1] in numerals)


def hanzi_and_pinyin(text):
    """Hanzi with words separated by spaces (for word-by-word speech) and pinyin with one
    syllable per character, punctuation as ASCII and the first syllable of a sentence capitalized."""
    # Spaces in the source are word boundaries (the CUV's space before 神, for one).
    words = [w for chunk in text.split() for w in jieba.cut(chunk) if w.strip()]
    hanzi_out, pinyin_out = [], []
    capital = True
    pending = ""                                           # opening quotes wait for the next word
    for i, word in enumerate(words):
        if all(c in OPENING for c in word):
            pending += word
            pinyin_out.append("".join(PUNCT.get(c, c) for c in word))
            continue
        if all(not is_han(c) for c in word):
            mark = "".join(PUNCT.get(c, c) for c in word)
            if hanzi_out and all(c in PUNCT or not c.isalnum() for c in word):
                hanzi_out[-1] += word                      # punctuation sticks to the word before it
            else:
                hanzi_out.append(word)
            pinyin_out.append(mark)
            if any(c in SENTENCE_END for c in word):
                capital = True
            continue
        chars = [c for c in word if is_han(c)]
        if word == "得" and i > 0 and words[i - 1] in DE_GET:
            syllables = ["dé"]
        elif word == "为" and any("所" in w for w in words[i + 1:i + 3]):
            syllables = ["wéi"]                            # 为…所: the passive, “be … by”
        elif word == "为" and i > 0 and words[i - 1] in WEI_AFTER:
            syllables = ["wéi"]                            # 便为有福: “is (blessed)”
        elif word in SINGLE:
            syllables = [SINGLE[word]]
        else:
            syllables = lazy_pinyin(word, style=Style.TONE, errors=lambda x: [c for c in x])
        syllables = sandhi(syllables, chars) if len(syllables) == len(chars) else syllables
        if capital and syllables:
            syllables[0] = syllables[0][:1].upper() + syllables[0][1:]
            capital = False
        hanzi_out.append(pending + word)
        pending = ""
        pinyin_out.extend(syllables)
    if pending:
        hanzi_out.append(pending)
    return " ".join(hanzi_out), " ".join(pinyin_out)


# ------------------------------------------------------------------------------------ editions
EDITIONS_FILE = os.path.join(TOOLS_BIBLE, "editions.json")
ZH_LABELS = {"cuv": "简体", "cuv-trad": "繁體"}


def load_editions():
    with open(EDITIONS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data["default"], data["editions"]


def version_list(value, lang):
    """'web,kjv' → ['web', 'kjv'], checked against VERSIONS; 'none' or '' → []."""
    names = [v.strip().lower() for v in (value or "").split(",") if v.strip()]
    if names in ([], ["none"]):
        return []
    for name in names:
        ok = name in ("cuv", "cuv-trad") if lang == "zh" else (name in VERSIONS and VERSIONS[name]["lang"] == lang)
        if not ok:
            choices = "cuv, cuv-trad" if lang == "zh" else ", ".join(k for k, v in VERSIONS.items() if v["lang"] == lang)
            raise SystemExit(f"Unknown {lang} version “{name}”. Choose from: {choices} (or none).")
    return names


# --------------------------------------------------------------------------------------- texts
def chinese(book, chapter, script):
    """{verse: text} of the CUV in 'cuv' (simplified) or 'cuv-trad' (traditional). Only the space
    before 神 (a mark of respect in the CUV) is kept, as a word boundary; the others are uneven."""
    out = {}
    for v, text in bs.load("cuv", book)["chapters"].get(chapter, {}).items():
        text = re.sub(r"\s+(?=神)", "\u0001", text)
        text = re.sub(r"\s+", "", text).replace("\u0001", " ")
        if script == "cuv":
            if not to_simplified:
                raise SystemExit("Simplified Chinese needs OpenCC:  pip3 install -r requirements.txt")
            text = to_simplified(text).replace("著", "着")   # the CUV's 著 is the particle 着
        out[v] = text
    return out


def strip_cantillation(text):
    """Keeps Hebrew letters and vowel points; drops the cantillation (accent) marks."""
    return "".join(c for c in text if not 0x0591 <= ord(c) <= 0x05AF)


def version_text(version, book, chapter):
    text = bs.load(version, book)["chapters"].get(chapter, {})
    if version == "wlc":
        text = {v: strip_cantillation(t) for v, t in text.items()}
    return text


def read_own_text(path, chapter):
    """'16 text' or '3:16 text' lines → {verse: text} (lines for other chapters are skipped)."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*(?:(\d+)\s*[:：])?\s*(\d+)\s+(.+)", line)
            if m and (m[1] is None or int(m[1]) == chapter):
                out[int(m[2])] = m[3].strip()
    return out


def same_words(simplified_spaced, traditional):
    """The traditional text split into the same words as the simplified one. Simplified and
    traditional CUV have the same characters one for one, so the word lengths carry over."""
    if not simplified_spaced:
        return ""
    chars = [c for c in traditional if not c.isspace()]
    if len(chars) != sum(1 for c in simplified_spaced if not c.isspace()):
        return to_traditional(simplified_spaced) if to_traditional else simplified_spaced
    out, i = [], 0
    for c in simplified_spaced:
        if c.isspace():
            out.append(c)
        else:
            out.append(chars[i])
            i += 1
    return "".join(out)


def cell(text):
    return (text or "").replace("|", "\\|").strip()


def study_list(value):
    """'krv,thkjv' → those keys, checked against VERSIONS (any language)."""
    names = [v.strip() for v in (value or "").split(",") if v.strip() and v.strip() != "none"]
    for name in names:
        if name not in VERSIONS:
            raise SystemExit(f"Unknown version “{name}” (bible_fetch.py --known lists them).")
    return names


def needed_sources(book, edition):
    """The source files (versions) an edition needs for one book."""
    needed = ["cuv"] if version_list(edition.get("zh", "cuv"), "zh") else []
    needed += [n for n in study_list(edition.get("study")) if bs.covers(n, book)]
    lang = "greek" if book >= NT_START else "hebrew"
    needed += version_list(edition.get(lang), lang)
    needed += [n for n in version_list(edition.get("en", "web"), "en") if bs.covers(n, book)]
    return needed


# --------------------------------------------------------------------------------------- pages
def page_name(book, chapter, v1, v2, edition, default):
    """romans-12.md, romans-12.classic.md, john-3-16.md, romans-8-28-39.md."""
    name = f"{bs.book_slug(book)}-{chapter}"
    if v1:
        name += f"-{v1}" + (f"-{v2}" if v2 and v2 != v1 else "")
    return name + ("" if edition == default else f".{edition}") + ".md"


def build_page(book, chapter, v1, v2, edition_name, edition, args):
    """One page: Hanzi | Pinyin | second Chinese script | Greek or Hebrew | English | others."""
    en_name, zh_name, zh_py, _ = BOOKS[book - 1]
    is_nt = book >= NT_START
    zh_versions = version_list(edition.get("zh", "cuv"), "zh")
    zh = chinese(book, chapter, "cuv") if zh_versions else {}
    trad = chinese(book, chapter, "cuv-trad") if "cuv-trad" in zh_versions else {}
    if args.hanzi_file:
        own = read_own_text(args.hanzi_file, chapter)
        zh.update({v: to_simplified(t) if to_simplified else t for v, t in own.items()})
        if trad:
            trad.update({v: to_traditional(t) if to_traditional else t for v, t in own.items()})

    originals = [n for n in version_list(edition.get("greek" if is_nt else "hebrew"), "greek" if is_nt else "hebrew")]
    translations = version_list(edition.get("en", "web"), "en")
    translations = [n for n in translations if bs.covers(n, book)]
    studies = [n for n in study_list(edition.get("study")) if bs.covers(n, book)]
    columns = []                          # (label, {verse: text}, description)
    for name in studies + originals[:1] + translations + originals[1:]:
        columns.append((VERSIONS[name]["label"], version_text(name, book, chapter), VERSIONS[name]["title"]))
    if args.english_file:
        columns.insert(1 if originals else 0, ("English", read_own_text(args.english_file, chapter),
                                               f"English from {os.path.basename(args.english_file)}"))
    paragraphs = []
    for name in translations:
        paragraphs = bs.load(name, book)["paragraphs"].get(chapter, [])
        if paragraphs:
            break

    verses = sorted(set(zh).union(*[set(c[1]) for c in columns]))
    if v1:
        verses = [v for v in verses if v1 <= v <= (v2 or v1)]
    if not verses:
        raise SystemExit(f"No verses for {en_name} {chapter}" + (f":{v1}" if v1 else "") + ".")

    span = "" if not v1 else f":{v1}" + (f"–{v2}" if v2 and v2 != v1 else "")
    title_zh = f"{zh_name} {chapter}" + span.replace(":", "：")
    title_py = f"{zh_py} {chapter}" + (f" : {span[1:]}" if span else "")
    title_en = f"{en_name} {chapter}{span}"

    # Groups: the English version's paragraphs, else runs of --group verses (5).
    starts = [v for v in paragraphs if v in verses] if not args.group else []
    if not starts:
        starts = verses[::args.group or 5]
    if verses[0] not in starts:
        starts.insert(0, verses[0])
    groups, current = [], []
    for v in verses:
        if v in starts and current:
            groups.append(current)
            current = []
        current.append(v)
    groups.append(current)

    sources = []
    if zh_versions and not args.hanzi_file:
        sources.append("和合本 (Chinese Union Version, 1919)" + (
            ", simplified and traditional" if len(zh_versions) > 1 else ", traditional" if zh_versions == ["cuv-trad"] else ""))
    if args.hanzi_file:
        sources.append(f"Hanzi from {os.path.basename(args.hanzi_file)}")
    sources += [c[2] + (", without cantillation marks" if c[0] == "WLC" else "") for c in columns]

    lines = ["<!-- reader: speak=word -->", "", f"# {title_zh} | {title_py} | {title_en}", "",
             f"> **{edition.get('title', edition_name)}** · " + " · ".join(sources), ""]
    second = zh_versions[1:]
    header = "| " + " | ".join(["Hanzi", "Pinyin"] + [ZH_LABELS[n] for n in second] + [c[0] for c in columns]) + " |"
    rule = "|" + "---|" * (2 + len(second) + len(columns))
    for group in groups:
        a, b = group[0], group[-1]
        nums = f"{a}" if a == b else f"{a}–{b}"
        lines += [f"## 第{nums}节 | Dì {nums} jié | {'Verse' if a == b else 'Verses'} {nums}", "",
                  "<!-- reader: table=verses -->", header, rule]
        for v in group:
            hz, py = hanzi_and_pinyin(zh[v]) if v in zh else ("", "")
            spaced = {"cuv": hz, "cuv-trad": same_words(hz, trad.get(v, ""))}
            main = spaced[zh_versions[0]] if zh_versions else ""
            row = ([f"{v} {main}".strip(), f"{v} {py}".strip()]
                   + [f"{v} {spaced[n]}".strip() for n in second]
                   + [c[1].get(v, "") for c in columns])
            lines.append("| " + " | ".join(cell(c) for c in row) + " |")
        lines.append("")
    for name in originals + translations:
        if VERSIONS[name].get("attribution"):
            lines += ["> " + VERSIONS[name]["attribution"], ""]
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------------------- index
TESTAMENTS = [("旧约 Old Testament", bs.OLD_TESTAMENT), ("新约 New Testament", bs.NEW_TESTAMENT)]
PASSAGES_HEADING = "### 经文 Passages"
PAGE_NAME = re.compile(r"^(?P<base>[a-z0-9-]+?-\d+(?:-\d+(?:-\d+)?)?)(?:\.(?P<edition>[a-z0-9_-]+))?\.md$")


def page_reference(path):
    """(book, chapter, v1, v2) from a passage page's title line, e.g. “… | Romans 12:1–8”."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("# "):
                english = line.rstrip().split("|")[-1].strip().replace("–", "-")
                book, ch, _ch2, v1, v2 = bs.parse_reference(english)
                return book, ch, v1, v2
    return None


def rebuild_index(text_repo):
    """Rewrites the 经文 Passages part of bible/README.md from the pages in bible/passages/:

        ### 经文 Passages
        #### 新约 New Testament
        ##### 罗马书 Romans
        - [12](passages/romans-12.md) · [Study](passages/romans-12.md) · [Classic](passages/romans-12.classic.md)

    One line per passage. With more than one edition, the line links each edition after the
    first link (the app's edition menu); with one edition it is just the first link. Books in Bible
    order, chapters and verses in number order; everything else in the file is kept."""
    default, editions = load_editions()
    order = list(editions)
    index = os.path.join(text_repo, "bible", "README.md")
    folder = os.path.join(text_repo, "bible", "passages")
    passages = {}                                  # (book, chapter, v1, v2) → {edition: file}
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        m = PAGE_NAME.match(name)
        if not m:
            continue
        try:
            ref = page_reference(os.path.join(folder, name))
        except SystemExit:
            ref = None
        if ref:
            passages.setdefault(ref, {})[m["edition"] or default] = name

    def edition_key(name):
        return (order.index(name), name) if name in order else (len(order), name)

    lines = [PASSAGES_HEADING, ""]
    for testament, books in TESTAMENTS:
        refs = sorted((r for r in passages if r[0] in books), key=lambda r: (r[0], r[1], r[2] or 0, r[3] or 0))
        if not refs:
            continue
        lines += [f"#### {testament}", ""]
        book = None
        for ref in refs:
            b, chapter, v1, v2 = ref
            if b != book:
                if book is not None:
                    lines.append("")
                en, zh, _py, _ = BOOKS[b - 1]
                lines += [f"##### {zh} {en}", ""]
                book = b
            label = f"{chapter}" + (f":{v1}" + (f"–{v2}" if v2 and v2 != v1 else "") if v1 else "")
            files = sorted(passages[ref].items(), key=lambda e: edition_key(e[0]))
            entry = f"- [{label}](passages/{files[0][1]})"
            if len(files) > 1:
                entry += "".join(f" · [{edition_title(editions, e)}](passages/{f})"
                                 for e, f in files)
            lines.append(entry)
        lines.append("")
    block = "\n".join(lines).rstrip() + "\n"

    with open(index, encoding="utf-8") as f:
        text = f.read()
    if PASSAGES_HEADING in text:
        head, rest = text.split(PASSAGES_HEADING, 1)
        m = re.search(r"\n#{2,3} ", rest)          # the block runs to the next ## or ### heading
        tail = rest[m.start():] if m else ""
        text = head.rstrip() + "\n\n" + block + (("\n" + tail.lstrip("\n")) if tail else "")
    else:
        text = text.rstrip() + "\n\n" + block
    with open(index, "w", encoding="utf-8") as f:
        f.write(text)
    return index, len(passages)


def edition_title(editions, name):
    """Study, Classic … from editions.json; a version's own label (KJV, 개역한글) for a version edition."""
    if name in editions:
        return editions[name].get("title", name.capitalize())
    return VERSIONS[name]["label"] if name in VERSIONS else name.capitalize()


def default_text_repo():
    """ChineseReaderText beside this tools repo (…/ChineseReaderTools/bible/bible_pages.py)."""
    if os.environ.get("CHINESEREADER_TEXT"):
        return os.environ["CHINESEREADER_TEXT"]
    return os.path.normpath(os.path.join(TOOLS_BIBLE, "..", "..", "ChineseReaderText"))


# ---------------------------------------------------------------------------------------- main
def show_editions():
    default, editions = load_editions()
    for name, e in editions.items():
        star = " (default)" if name == default else ""
        print(f"{name}{star}: {e.get('title', name)}")
        for lang in ("zh", "en", "greek", "hebrew"):
            print(f"    {lang:7} {e.get(lang, '-')}")
    print("\nversions:")
    for key, v in VERSIONS.items():
        print(f"    {key:10} {v['lang']:7} {v['title']}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("references", nargs="*", help='e.g. Romans, "Romans 12", "Romans 12-14", "罗马书 12:1-8"')
    p.add_argument("--edition", help="edition(s) from editions.json, comma-separated (default: its default)")
    p.add_argument("--all-editions", action="store_true", help="every edition in editions.json")
    p.add_argument("--zh", help="override: cuv, cuv-trad, cuv,cuv-trad or none")
    p.add_argument("--en", help="override: English versions, comma-separated")
    p.add_argument("--greek", help="override: Greek versions for the New Testament")
    p.add_argument("--hebrew", help="override: Hebrew versions for the Old Testament")
    p.add_argument("--study", help="versions in other study languages (Korean, Thai …), shown right after "
                                   "the Chinese: krv, thkjv …")
    p.add_argument("--as", dest="as_name", help="with overrides: save as this one-off edition (file romans-12.<name>.md)")
    p.add_argument("--hanzi-file", help="your own Hanzi, one verse per line (“16 text”)")
    p.add_argument("--english-file", help="your own English, one verse per line")
    p.add_argument("--group", type=int, default=0, help="verses per group (default: the English paragraphs, else 5)")
    p.add_argument("--text-repo", default=default_text_repo(),
                   help="the ChineseReaderText folder (default: beside ChineseReaderTools, or $CHINESEREADER_TEXT)")
    p.add_argument("--no-index", action="store_true", help="don't update the 经文 Passages list")
    p.add_argument("--index-only", action="store_true", help="only rebuild the 经文 Passages list")
    p.add_argument("--stdout", action="store_true", help="print the pages instead of writing them")
    p.add_argument("--editions", action="store_true", help="list the editions and versions, and stop")
    args = p.parse_args()

    if args.editions:
        show_editions()
        return
    if args.index_only:
        index, count = rebuild_index(args.text_repo)
        print(f"listed {count} passages in {index}")
        return
    if not args.references:
        p.error('give at least one reference, e.g. Romans or "Romans 12"')
    if not HAVE_PINYIN:
        p.error("building pages needs pypinyin and jieba:  pip3 install -r requirements.txt")
    if not args.stdout and not os.path.isdir(os.path.join(args.text_repo, "bible")):
        p.error(f"no bible/ folder in {args.text_repo}: give --text-repo /path/to/ChineseReaderText")

    default, editions = load_editions()
    overrides = {k: getattr(args, k) for k in ("zh", "en", "greek", "hebrew", "study") if getattr(args, k)}
    if args.as_name:
        if not re.fullmatch(r"[a-z0-9_-]+", args.as_name):
            p.error("--as takes a short lowercase name, e.g. compare")
        base = editions[default]
        title = VERSIONS[args.as_name]["label"] if args.as_name in VERSIONS else args.as_name.capitalize()
        chosen = [(args.as_name, {**base, "title": title, **overrides})]
    else:
        names = list(editions) if args.all_editions else (args.edition or default).split(",")
        for name in names:
            if name.strip() not in editions:
                p.error(f"no edition “{name}” in editions.json (have: {', '.join(editions)})")
        chosen = [(n.strip(), {**editions[n.strip()], **overrides}) for n in names]

    # Every source the pages need, checked before anything is written.
    refs = [bs.parse_reference(text) for text in args.references]
    missing = set()
    for book, *_ in refs:
        for _name, edition in chosen:
            for version in needed_sources(book, edition):
                if not os.path.exists(bs.source_path(version, book)):
                    missing.add((version, BOOKS[book - 1][0]))
    if missing:
        books = sorted({b for _, b in missing})
        versions = sorted({v for v, _ in missing})
        print("Not in sources/ yet: " + ", ".join(f"{v} {b}" for v, b in sorted(missing)))
        print(f"Fetch them first:  cd {SOURCES_REPO} && python3 common/scripts/bible_fetch.py "
              f"{' '.join(repr(b) if ' ' in b else b for b in books)} --versions {','.join(versions)}")
        sys.exit(1)

    written = []
    folder = os.path.join(args.text_repo, "bible", "passages")
    for book, ch, ch2, v1, v2 in refs:
        for name, edition in chosen:
            if ch is None:          # a whole book: every chapter its Chinese (or first) source has
                first = "cuv" if edition.get("zh", "cuv") != "none" else version_list(edition.get("en"), "en")[0]
                chapters = sorted(bs.load(first, book)["chapters"])
            else:
                chapters = range(ch, ch2 + 1)
            for chapter in chapters:
                page = build_page(book, chapter, v1, v2, name, edition, args)
                if args.stdout:
                    print(page)
                    continue
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, page_name(book, chapter, v1, v2, name, default))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(page)
                written.append(os.path.relpath(path, args.text_repo))
    for path in written:
        print(f"wrote {path}")
    if written and not args.no_index:
        index, count = rebuild_index(args.text_repo)
        print(f"listed {count} passages in {os.path.relpath(index, args.text_repo)}")
        print("Ready to check in: git -C ../ChineseReaderText status bible/")


if __name__ == "__main__":
    main()
