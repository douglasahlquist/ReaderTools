#!/usr/bin/env python3
"""Builds HSK course lessons for ChineseReaderText from short source files, in the same format as
the HSK 1 and HSK 2 lessons (hsk-2021/hsk2/05.md), and checks that every sentence uses only words
already taught.

A lesson source (hsk/hsk3/05.txt) is plain text; Hanzi are written with spaces between words:

    goal: Talk about the four seasons and the weather.
    @word 春天 | spring
    春天 来 了！ | Spring is here!
    @word 转 [zhuǎn] | to turn                    ← a reading for the header when the list's is odd
    @grammar 多了 | Adjective + 多了: much more
    > After an adjective, **多了** means “much more so”.
    凉快 多 了。 | It's much cooler.
    @dialog Tomorrow's weather
    Mama：明天 天气 怎么样？ | What's the weather tomorrow?

A word's reading can be given in a sentence as 地{de} when the usual one is wrong there.

    python3 hsk/hsk_lessons.py build 3            # every lesson that has a source → hsk-2021/hsk3/NN.md
    python3 hsk/hsk_lessons.py build 3 1 2 3      # only these
    python3 hsk/hsk_lessons.py check 3            # vocabulary check only
    python3 hsk/hsk_lessons.py index 3            # 00.md and the course list only (build does this too)
"""
import argparse
import collections
import glob
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_REPO = os.environ.get("CHINESEREADER_TEXT") or os.path.normpath(os.path.join(HERE, "..", "..", "ChineseReaderText"))
COURSE = "hsk-2021"
NUMERALS = "零一二三四五六七八九"
PUNCT = {"，": ",", "。": ".", "；": ";", "：": ":", "？": "?", "！": "!", "、": ",", "“": "“", "”": "”",
         "‘": "‘", "’": "’", "（": "(", "）": ")", "《": "«", "》": "»", "…": "…", "—": "—"}
SENTENCE_END = set("。？！")
# Names and other words that may appear without being taught.
NAMES = {"小明", "小红", "小王", "小李", "王", "李", "大卫", "安娜", "教会", "上帝", "耶稣", "圣经"}
# Speaker labels in dialogs (Latin, as in HSK 1 and 2).


def is_han(ch):
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


def chinese_number(n):
    if n <= 10:
        return "十" if n == 10 else NUMERALS[n]
    if n < 20:
        return "十" + (NUMERALS[n % 10] if n % 10 else "")
    return NUMERALS[n // 10] + "十" + (NUMERALS[n % 10] if n % 10 else "")


# ------------------------------------------------------------------------------- what's taught
def lesson_files(level):
    return sorted(f for f in glob.glob(os.path.join(TEXT_REPO, COURSE, f"hsk{level}", "[0-9][0-9].md"))
                  if not f.endswith("00.md"))


def glossary_words(path):
    text = open(path, encoding="utf-8").read()
    m = re.search(r"## 生词 \|.*?\n\n<!-- reader: table=glossary -->\n\| Hanzi.*?\n\|---.*?\n((?:\|.*\n)+)", text)
    return [row.strip("|").split("|")[0].strip().replace(" ", "") for row in m.group(1).splitlines()] if m else []


def taught_before(level):
    words = set()
    for lv in range(1, level):
        for f in lesson_files(lv):
            words.update(glossary_words(f))
    return words


def readings_from_lessons(max_level):
    """Word → syllables as written in the existing lessons (the most common way), and proper nouns."""
    counts = collections.defaultdict(collections.Counter)
    proper = set()
    for lv in range(1, max_level + 1):
        for f in lesson_files(lv):
            for line in open(f, encoding="utf-8"):
                if not line.startswith("| ") or line.startswith("| Hanzi"):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 3:
                    continue
                hanzi = re.sub(r"^[A-Za-z]+：", "", cells[0])
                tokens = [t for t in hanzi.split() if any(is_han(c) for c in t)]
                syllables = [s for s in cells[1].split() if re.search(r"[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]", s)]
                if sum(sum(is_han(c) for c in t) for t in tokens) != len(syllables):
                    continue
                # Where each syllable sits in the pinyin cell, to tell sentence starts from names.
                positions = [k for k, s in enumerate(cells[1].split()) if s in syllables]
                pin_tokens = cells[1].split()
                i = 0
                for t in tokens:
                    word = "".join(c for c in t if is_han(c))
                    syl = syllables[i:i + len(word)]
                    if i < len(positions):
                        pos = positions[i]
                        starts = pos == 0 or pin_tokens[pos - 1] in {".", "?", "!", "“", "(", ":"}
                        if syl[0][:1].isupper() and not starts:
                            proper.add(word)
                    i += len(word)
                    counts[word][" ".join(s.lower() for s in syl)] += 1
    return {w: c.most_common(1)[0][0] for w, c in counts.items()}, proper


def vocabulary(level):
    path = glob.glob(os.path.join(TEXT_REPO, "characters", "data", f"hsk{level}-0001-*.json"))[0]
    return {i["simplified"]: i for i in json.load(open(path, encoding="utf-8"))["items"]}


def plan(level):
    lessons = []
    for line in open(os.path.join(HERE, f"hsk{level}_plan.txt"), encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        n, zh, en, words = [x.strip() for x in line.split("|")]
        lessons.append(dict(number=int(n), zh=zh, en=en, words=words.split()))
    return lessons


# ------------------------------------------------------------------------------------ pinyin
class Pinyin:
    def __init__(self, level):
        self.known, self.proper = readings_from_lessons(level - 1)
        self.proper |= {n for n in NAMES if n not in {"教会"}}
        self.new = collections.Counter()           # words read with pypinyin: to look over
        from pypinyin import Style, lazy_pinyin
        self.lazy = lambda w: lazy_pinyin(w, style=Style.TONE, errors=lambda x: list(x))

    def word(self, word):
        if word in {"一", "不", "了", "地"}:            # base readings: the tone rules below change 一 and 不
            return [{"一": "yī", "不": "bù", "了": "le", "地": "de"}[word]]
        if word in self.known:
            return self.known[word].split()
        # Erhua as the HSK 1–2 lessons write it: 会儿 huì r, 玩儿 wán r.
        if len(word) >= 2 and word.endswith("儿"):
            return self.word(word[:-1]) + ["r"]
        # A doubled verb takes a neutral tone on its second syllable: 看看 kàn kan.
        if len(word) == 2 and word[0] == word[1] and word[0] in "看问想试说听等走找学写读尝谈坐玩开拍推拿洗讲练动跑聊唱跳摸用算查":
            first = self.word(word[0])[0]
            return [first, Pinyin.neutral(first)]
        if word in {"了"}:
            return ["le"]
        self.new[word] += 1
        return self.lazy(word)

    @staticmethod
    def neutral(s):
        return "".join(c for c in unicodedata.normalize("NFD", s) if c not in "̄́̌̀")

    @staticmethod
    def tone(s):
        for c in unicodedata.normalize("NFD", s):
            if c in "̄́̌̀":
                return {"̄": 1, "́": 2, "̌": 3, "̀": 4}[c]
        return 5

    def line(self, text):
        """'春天 来 了！' → '春天 来 了！', 'Chūn tiān lái le !' (overrides 地{de} removed from the Hanzi)."""
        hanzi_out, pin_out = [], []
        capital = True
        chars_all, syl_all = [], []
        for token in text.split():
            m = re.fullmatch(r"(.*?)\{([^}]*)\}(.*)", token)
            given = None
            if m:
                token, given = m.group(1) + m.group(3), m.group(2).split()
            hanzi_out.append(token)
            # Leading and trailing punctuation around the word.
            lead = "".join(c for c in re.match(r"^[^\w]*", token).group(0))
            core = token[len(lead):]
            trail = re.search(r"[^\w]*$", core).group(0)
            core = core[:len(core) - len(trail)] if trail else core
            for c in lead:
                pin_out.append(PUNCT.get(c, c))
            if core:
                if all(is_han(c) for c in core):
                    syl = list(given or self.word(core))
                    if core in self.proper and syl:
                        syl[0] = syl[0][:1].upper() + syl[0][1:]
                    for c, s in zip(core, syl):
                        chars_all.append(c)
                        syl_all.append((len(pin_out), s))
                        pin_out.append(s)
                else:
                    pin_out.append(core)
            for c in trail:
                pin_out.append(PUNCT.get(c, c))
        # 不 and 一 before the next syllable's tone.
        for k, (c, (pos, s)) in enumerate(zip(chars_all, syl_all)):
            if k + 1 >= len(syl_all):
                break
            nxt = self.tone(syl_all[k + 1][1])
            prev = chars_all[k - 1] if k else ""
            nxtc = chars_all[k + 1]
            if c == "不" and s == "bù" and nxt == 4:
                pin_out[pos] = "bú"
            elif c == "一" and s == "yī" and prev not in "第十" + NUMERALS and nxtc not in NUMERALS + "十百千万":
                pin_out[pos] = "yí" if nxt == 4 else "yì" if nxt in (1, 2, 3) else "yī"
        # Capitals: the first syllable of each sentence, and proper nouns.
        out = []
        for tok in pin_out:
            if capital and re.match(r"[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]", tok):
                tok = tok[:1].upper() + tok[1:]
                capital = False
            if tok in {".", "?", "!"}:
                capital = True
            out.append(tok)
        return " ".join(hanzi_out), " ".join(out)


# ------------------------------------------------------------------------------------ sources
def read_source(path):
    lesson = dict(goal="", words=[], grammar=[], dialogs=[])
    current = None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        if line.startswith(("title:", "zh:")):
            continue
        if line.startswith("goal:"):
            lesson["goal"] = line[5:].strip()
        elif line.startswith("@word "):
            head, _, gloss = line[6:].partition("|")
            m = re.fullmatch(r"\s*(\S+)\s*(?:\[([^\]]+)\])?\s*", head)
            current = dict(word=m.group(1), reading=m.group(2), gloss=gloss.strip(), lines=[])
            lesson["words"].append(current)
        elif line.startswith("@grammar "):
            head, _, title = line[9:].partition("|")
            current = dict(head=head.strip(), title=title.strip(), note=[], lines=[])
            lesson["grammar"].append(current)
        elif line.startswith("@dialog "):
            current = dict(title=line[8:].strip(), lines=[])
            lesson["dialogs"].append(current)
        elif line.startswith(">"):
            current["note"].append(line[1:].strip())
        else:
            zh, _, en = line.partition("|")
            current["lines"].append((zh.strip(), en.strip()))
    return lesson


def tokens_of(text):
    text = re.sub(r"^[A-Za-z]+：", "", text)
    out = []
    for t in text.split():
        t = re.sub(r"\{[^}]*\}", "", t)
        core = "".join(c for c in t if is_han(c))
        if core:
            out.append(core)
    return out


def allowed_token(token, allowed):
    if token in allowed or token in NAMES:
        return True
    if all(c in NUMERALS + "十百千万两半第" for c in token):
        return True
    if len(token) == 2 and token[0] == token[1] and token[0] in allowed:      # 看看, 慢慢
        return True
    if len(token) == 4 and token[:2] == token[2:] and token[:2] in allowed:
        return True
    if len(token) >= 2 and token[-1] in "们儿" and token[:-1] in allowed:
        return True
    return False


def check(level, numbers=None, quiet=False):
    taught = taught_before(level)
    course = plan(level)
    allowed = set(taught)
    problems = 0
    for lesson in course:
        allowed.update(lesson["words"])
        path = os.path.join(HERE, f"hsk{level}", f"{lesson['number']:02d}.txt")
        if not os.path.exists(path) or (numbers and lesson["number"] not in numbers):
            continue
        src = read_source(path)
        listed = [w["word"] for w in src["words"]]
        if listed != lesson["words"]:
            print(f"Lesson {lesson['number']}: words differ from the plan: {listed} vs {lesson['words']}")
            problems += 1
        blocks = [("word " + w["word"], w["lines"]) for w in src["words"]] + \
                 [("grammar " + g["head"], g["lines"]) for g in src["grammar"]] + \
                 [("dialog " + d["title"], d["lines"]) for d in src["dialogs"]]
        for name, lines in blocks:
            for zh, en in lines:
                bad = [t for t in tokens_of(zh) if not allowed_token(t, allowed)]
                if not en:
                    print(f"Lesson {lesson['number']} {name}: no English: {zh}")
                    problems += 1
                if bad:
                    print(f"Lesson {lesson['number']} {name}: not taught yet: {' '.join(bad)}  ← {zh}")
                    problems += 1
    if not quiet:
        print(f"{problems} problem(s)")
    return problems


# ------------------------------------------------------------------------------------ build
def build(level, numbers=None):
    vocab = vocabulary(level)
    py = Pinyin(level)
    course = plan(level)
    out_dir = os.path.join(TEXT_REPO, COURSE, f"hsk{level}")
    os.makedirs(out_dir, exist_ok=True)
    built = []
    for lesson in course:
        n = lesson["number"]
        path = os.path.join(HERE, f"hsk{level}", f"{n:02d}.txt")
        if not os.path.exists(path) or (numbers and n not in numbers):
            continue
        src = read_source(path)
        title_zh = f"第{chinese_number(n)}课：{lesson['zh']}"
        _, title_py = py.line(" ".join(_segment(title_zh)))
        md = ["<!-- reader: speak=word -->",
              f"# {title_zh} | {title_py} | HSK {level} · Lesson {n}: {lesson['en']}", "",
              "> **Draft** — not yet reviewed by a native speaker.", "",
              f"> **Goal:** {src['goal']}", "",
              f"## 生词 | Shēng cí | New words ({len(src['words'])})", "",
              "<!-- reader: table=glossary -->", "| Hanzi | Pinyin | English |", "|---|---|---|"]
        heads = []
        for w in src["words"]:
            reading = w["reading"] or " ".join(_syllables(vocab.get(w["word"]), w["word"], py))
            heads.append(reading)
            md.append(f"| {w['word']} | {reading} | {w['gloss']} |")
        md.append("")
        for i, (w, reading) in enumerate(zip(src["words"], heads), 1):
            md += [f"## 生词{i}：{w['word']} | Shēng cí {i} : {reading} | Word {i}: {reading} — {w['gloss']}", ""]
            md += _table(w["lines"], py)
        for g in src["grammar"]:
            _, head_py = py.line(" ".join(_segment(g["head"])))
            md += [f"## 语法：{g['head']} | Yǔ fǎ : {head_py[:1].lower() + head_py[1:]} | Grammar: {g['title']}", ""]
            for note in g["note"]:
                md += [f"> {note}", ""]
            if g["lines"]:
                md += _table(g["lines"], py)
        for i, d in enumerate(src["dialogs"], 1):
            md += [f"## 对话{chinese_number(i)} | Duì huà {py.word(chinese_number(i))[0] if i < 11 else chinese_number(i)} | Dialog {i} · {d['title']}", ""]
            md += _table(d["lines"], py, dialog=True)
        with open(os.path.join(out_dir, f"{n:02d}.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(md).rstrip() + "\n")
        built.append(n)
    print(f"built {len(built)} lesson(s): {built}")
    if py.new:
        print("Readings from pypinyin (not in the HSK 1–2 lessons) — look these over:")
        print("  " + "  ".join(f"{w} {' '.join(py.lazy(w))}" for w, _ in sorted(py.new.items())))
    return built


INTRO = {3: dict(
    words=953, lessons_note="It adds about 970 words to the 1,250 of HSK 1 and 2.",
    already="One HSK 3 word was already taught in HSK 1 and isn't repeated: 钟 (HSK 1, lesson 52).",
    outcome="By the end you can talk about work, school, news, sport, travel, health and feelings; link "
            "ideas with 因此, 由于, 不仅 and 除了; use 把 and 被; give opinions and reasons; and follow "
            "longer conversations at home, at church and in town.")}


def index(level):
    """hsk{level}/00.md (about the level, every lesson listed) and the level's section of the course list."""
    py = Pinyin(level)
    course = plan(level)
    info = INTRO[level]
    out_dir = os.path.join(TEXT_REPO, COURSE, f"hsk{level}")
    built = [l for l in course if os.path.exists(os.path.join(out_dir, f"{l['number']:02d}.md"))]
    n_words = sum(len(l["words"]) for l in course)
    zh_level = chinese_number(level)
    md = ["<!-- reader: speak=word -->",
          f"# HSK {level} 介绍 | HSK {py.word(zh_level)[0]} jiè shào | About HSK {level}", "",
          "> **Draft** — the lessons are not yet reviewed by a native speaker.", "",
          "## 目标 | Mù biāo | The goal", "",
          f"> HSK {level} is the level {level} of the HSK 3.0 standard (2021). {info['lessons_note']} This course "
          f"teaches the **{n_words} HSK {level} words** not already met in the earlier lessons, in **{len(course)} lessons** "
          f"of about {round(n_words / len(course))} new words each. Every sentence uses only words from the earlier levels "
          f"and the HSK {level} words taught before it.", "",
          f"> {info['outcome']}", "",
          "## 每课 | Měi kè | How each lesson works", "",
          "> Each lesson works like HSK 1 and 2: the goal and an always-visible word list first, then about eight "
          "sentences for each new word, grammar notes, and dialogs that use everything learned so far. Tap a word for "
          "its pinyin and sound; double-tap a line for its English.", "",
          f"> {info['already']}", "",
          "## 课文 | Kè wén | The lessons", "",
          "<!-- reader: table=glossary -->", "| Hanzi | Pinyin | English |", "|---|---|---|"]
    for l in course:
        title = f"第{chinese_number(l['number'])}课：{l['zh']}"
        _, title_py = py.line(" ".join(_segment(title)))
        md.append(f"| {title} | {title_py} | {l['en']} |")
    with open(os.path.join(out_dir, "00.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    # The course list: this level's section, with the lessons built so far.
    readme = os.path.join(TEXT_REPO, COURSE, "README.md")
    text = open(readme, encoding="utf-8").read()
    vocab = os.path.basename(glob.glob(os.path.join(TEXT_REPO, "characters", "data", f"hsk{level}-0001-*.json"))[0])
    count = re.search(r"-(\d+)\.json$", vocab).group(1).lstrip("0")
    lines = [f"### HSK {level} · 第{zh_level}级", "",
             f"- [HSK {level} · 1–{count} · 词汇 Vocabulary](../characters/data/{vocab})",
             f"- [HSK {level} 介绍 · About HSK {level}](hsk{level}/00.md)"]
    lines += [f"- [第{chinese_number(l['number'])}课：{l['zh']} · {l['en']}](hsk{level}/{l['number']:02d}.md)" for l in built]
    section = "\n".join(lines) + "\n"
    pattern = re.compile(rf"### HSK {level} · .*?(?=\n### |\Z)", re.S)
    text = pattern.sub(lambda _m: section, text) if pattern.search(text) else text.rstrip("\n") + "\n\n" + section
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    print(f"wrote hsk{level}/00.md ({len(course)} lessons) and the HSK {level} section of {COURSE}/README.md ({len(built)} built)")


def _syllables(entry, word, py):
    if entry and entry.get("syllables") and len(entry["syllables"]) == len(word):
        return entry["syllables"]
    return py.word(word)


def _segment(text):
    import jieba
    jieba.setLogLevel(60)
    return [w for w in jieba.cut(text) if w.strip()]


def _table(lines, py, dialog=False):
    rows = ["| Hanzi | Pinyin | English |", "|---|---|---|"]
    for zh, en in lines:
        speaker = ""
        m = re.match(r"^([A-Za-z]+)：(.*)$", zh)
        if dialog and m:
            speaker, zh = m.group(1) + "：", m.group(2)
        hanzi, pinyin = py.line(zh)
        rows.append(f"| {speaker}{hanzi} | {pinyin} | {en} |")
    return rows + [""]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["build", "check", "index"])
    p.add_argument("level", type=int)
    p.add_argument("lessons", nargs="*", type=int)
    args = p.parse_args()
    numbers = set(args.lessons) or None
    if args.command == "index":
        index(args.level)
        return
    problems = check(args.level, numbers)
    if args.command == "build":
        if problems:
            print("(building anyway: fix the problems above)")
        build(args.level, numbers)
        index(args.level)


if __name__ == "__main__":
    main()
