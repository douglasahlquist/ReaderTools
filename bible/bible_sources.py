"""What bible_fetch.py and bible_pages.py share: the books, Bible references, the versions,
and the source texts kept in ChineseReaderTools/sources/.

A source file holds one book of one version, as downloaded and cleaned:

    sources/web/45-romans.json
    {"version": "web", "book": 45, "name": "Romans",
     "chapters": {"12": {"1": "Therefore I urge you, …", …}, …},
     "paragraphs": {"12": [1, 3, 9, 20, 21], …}}          (only versions that mark paragraphs)

`sources/cuv/` holds the Chinese Union Version as published (traditional, with its spacing);
bible_pages.py makes the simplified text from it.
"""
import json
import os
import re
import sys
import urllib.request

try:
    from opencc import OpenCC
    _t2s = OpenCC("t2s")
    _s2t = OpenCC("s2t")
    def to_simplified(text): return _t2s.convert(text)
    def to_traditional(text): return _s2t.convert(text)
except Exception:  # only without opencc
    to_simplified = to_traditional = None

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.environ.get("BIBLE_SOURCES") or os.path.normpath(os.path.join(HERE, "..", "sources"))
DOWNLOADS = os.path.expanduser(os.environ.get("BIBLE_CACHE", "~/.cache/chinesereader-bible"))

SCROLLMAPPER = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/{}.json"
WEB = "https://raw.githubusercontent.com/TehShrike/world-english-bible/master/json/{}.json"
SBLGNT = "https://raw.githubusercontent.com/morphgnt/sblgnt/master/{}-morphgnt.txt"

# ------------------------------------------------------------------------------------- books
# (English name, Chinese name, its pinyin, other English names and abbreviations)
BOOKS = [
    ("Genesis", "创世记", "Chuàng shì jì", "gen ge gn"),
    ("Exodus", "出埃及记", "Chū āi jí jì", "exod exo ex"),
    ("Leviticus", "利未记", "Lì wèi jì", "lev le lv"),
    ("Numbers", "民数记", "Mín shù jì", "num nu nm nb"),
    ("Deuteronomy", "申命记", "Shēn mìng jì", "deut de dt"),
    ("Joshua", "约书亚记", "Yuē shū yà jì", "josh jos"),
    ("Judges", "士师记", "Shì shī jì", "judg jdg jg"),
    ("Ruth", "路得记", "Lù dé jì", "ru rth"),
    ("1 Samuel", "撒母耳记上", "Sā mǔ ěr jì shàng", "1sam 1sa 1sm"),
    ("2 Samuel", "撒母耳记下", "Sā mǔ ěr jì xià", "2sam 2sa 2sm"),
    ("1 Kings", "列王纪上", "Liè wáng jì shàng", "1kgs 1ki 1kg"),
    ("2 Kings", "列王纪下", "Liè wáng jì xià", "2kgs 2ki 2kg"),
    ("1 Chronicles", "历代志上", "Lì dài zhì shàng", "1chr 1ch"),
    ("2 Chronicles", "历代志下", "Lì dài zhì xià", "2chr 2ch"),
    ("Ezra", "以斯拉记", "Yǐ sī lā jì", "ezr"),
    ("Nehemiah", "尼希米记", "Ní xī mǐ jì", "neh ne"),
    ("Esther", "以斯帖记", "Yǐ sī tiē jì", "esth est es"),
    ("Job", "约伯记", "Yuē bó jì", "jb"),
    ("Psalms", "诗篇", "Shī piān", "psalm ps psa pss"),
    ("Proverbs", "箴言", "Zhēn yán", "prov pro pr prv"),
    ("Ecclesiastes", "传道书", "Chuán dào shū", "eccl ecc ec qoh"),
    ("Song of Songs", "雅歌", "Yǎ gē", "song of solomon song sos ss canticles"),
    ("Isaiah", "以赛亚书", "Yǐ sài yà shū", "isa is"),
    ("Jeremiah", "耶利米书", "Yē lì mǐ shū", "jer je jr"),
    ("Lamentations", "耶利米哀歌", "Yē lì mǐ āi gē", "lam la"),
    ("Ezekiel", "以西结书", "Yǐ xī jié shū", "ezek eze ezk"),
    ("Daniel", "但以理书", "Dàn yǐ lǐ shū", "dan da dn"),
    ("Hosea", "何西阿书", "Hé xī ā shū", "hos ho"),
    ("Joel", "约珥书", "Yuē ěr shū", "jl"),
    ("Amos", "阿摩司书", "Ā mó sī shū", "am"),
    ("Obadiah", "俄巴底亚书", "É bā dǐ yà shū", "obad ob"),
    ("Jonah", "约拿书", "Yuē ná shū", "jon jnh"),
    ("Micah", "弥迦书", "Mí jiā shū", "mic mc"),
    ("Nahum", "那鸿书", "Nà hóng shū", "nah na"),
    ("Habakkuk", "哈巴谷书", "Hā bā gǔ shū", "hab hb"),
    ("Zephaniah", "西番雅书", "Xī fān yǎ shū", "zeph zep zp"),
    ("Haggai", "哈该书", "Hā gāi shū", "hag hg"),
    ("Zechariah", "撒迦利亚书", "Sā jiā lì yà shū", "zech zec zc"),
    ("Malachi", "玛拉基书", "Mǎ lā jī shū", "mal ml"),
    ("Matthew", "马太福音", "Mǎ tài fú yīn", "matt mat mt"),
    ("Mark", "马可福音", "Mǎ kě fú yīn", "mrk mk mr"),
    ("Luke", "路加福音", "Lù jiā fú yīn", "luk lk"),
    ("John", "约翰福音", "Yuē hàn fú yīn", "jhn jn"),
    ("Acts", "使徒行传", "Shǐ tú xíng zhuàn", "act ac"),
    ("Romans", "罗马书", "Luó mǎ shū", "rom ro rm"),
    ("1 Corinthians", "哥林多前书", "Gē lín duō qián shū", "1cor 1co"),
    ("2 Corinthians", "哥林多后书", "Gē lín duō hòu shū", "2cor 2co"),
    ("Galatians", "加拉太书", "Jiā lā tài shū", "gal ga"),
    ("Ephesians", "以弗所书", "Yǐ fú suǒ shū", "eph ephes"),
    ("Philippians", "腓立比书", "Féi lì bǐ shū", "phil php pp"),
    ("Colossians", "歌罗西书", "Gē luó xī shū", "col"),
    ("1 Thessalonians", "帖撒罗尼迦前书", "Tiē sā luó ní jiā qián shū", "1thess 1th"),
    ("2 Thessalonians", "帖撒罗尼迦后书", "Tiē sā luó ní jiā hòu shū", "2thess 2th"),
    ("1 Timothy", "提摩太前书", "Tí mó tài qián shū", "1tim 1ti"),
    ("2 Timothy", "提摩太后书", "Tí mó tài hòu shū", "2tim 2ti"),
    ("Titus", "提多书", "Tí duō shū", "tit ti"),
    ("Philemon", "腓利门书", "Féi lì mén shū", "philem phm pm"),
    ("Hebrews", "希伯来书", "Xī bó lái shū", "heb"),
    ("James", "雅各书", "Yǎ gè shū", "jas jm"),
    ("1 Peter", "彼得前书", "Bǐ dé qián shū", "1pet 1pe 1pt"),
    ("2 Peter", "彼得后书", "Bǐ dé hòu shū", "2pet 2pe 2pt"),
    ("1 John", "约翰一书", "Yuē hàn yī shū", "1jn 1jo 1jhn"),
    ("2 John", "约翰二书", "Yuē hàn èr shū", "2jn 2jo 2jhn"),
    ("3 John", "约翰三书", "Yuē hàn sān shū", "3jn 3jo 3jhn"),
    ("Jude", "犹大书", "Yóu dà shū", "jud jd"),
    ("Revelation", "启示录", "Qǐ shì lù", "rev re revelations apocalypse"),
]
NT_START = 40  # book number of Matthew (Genesis is 1)
OLD_TESTAMENT = range(1, NT_START)
NEW_TESTAMENT = range(NT_START, len(BOOKS) + 1)
SBLGNT_CODES = ["Mt", "Mk", "Lk", "Jn", "Ac", "Ro", "1Co", "2Co", "Ga", "Eph", "Php", "Col", "1Th", "2Th",
                "1Ti", "2Ti", "Tit", "Phm", "Heb", "Jas", "1Pe", "2Pe", "1Jn", "2Jn", "3Jn", "Jud", "Re"]


def book_slug(book):
    """45 → "romans", 46 → "1-corinthians" (used in file names)."""
    return re.sub(r"[^a-z0-9]+", "-", BOOKS[book - 1][0].lower()).strip("-")


def _key(name):
    return re.sub(r"[\s.]", "", name.lower())


BOOK_KEYS = {}
for _number, (_en, _zh, _py, _others) in enumerate(BOOKS, start=1):
    for _name in [_en, _zh] + _others.split():
        BOOK_KEYS[_key(_name)] = _number
    if to_traditional:
        BOOK_KEYS[_key(to_traditional(_zh))] = _number
    BOOK_KEYS.setdefault(_key(_zh.rstrip("书记")), _number)           # 罗马 → 罗马书
for _alias, _en in [("psalm", "Psalms"), ("诗", "Psalms"), ("songofsolomon", "Song of Songs")]:
    BOOK_KEYS[_key(_alias)] = [b[0] for b in BOOKS].index(_en) + 1


def find_book(name):
    key = _key(name)
    if key in BOOK_KEYS:
        return BOOK_KEYS[key]
    if to_simplified and _key(to_simplified(name)) in BOOK_KEYS:
        return BOOK_KEYS[_key(to_simplified(name))]
    # "1 Cor" → "1cor": a unique prefix of an English name.
    hits = {n for k, n in BOOK_KEYS.items() if k.startswith(key) and key[:1].isalnum() and len(key) >= 3}
    if len(hits) == 1:
        return hits.pop()
    raise SystemExit(f"Don't know the book “{name}”.")


def _book_number(name):
    """A book name as a source writes it ("I Samuel", "Revelation of John") → its number, or None."""
    name = re.sub(r"^(III|II|I)\s", lambda m: f"{len(m[1])} ", name.strip())
    try:
        return find_book(name)
    except SystemExit:
        return None


# A reference: "Romans", "Romans 12", "Romans 12-14", "Romans 12:1-8", "罗马书 12", "罗马书第12章".
REF = re.compile(r"""^\s*(?P<book>.*?\D)\s*第?\s*
                     (?:(?P<ch>\d+)\s*[章篇]?
                        (?:\s*[-–—~至到]\s*(?P<ch2>\d+)\s*[章篇]?(?!\s*[:：]))?
                        (?:\s*[:：]\s*(?P<v1>\d+)(?:\s*[-–—~至到]\s*(?P<v2>\d+))?\s*节?)?)?\s*$""", re.X)


def parse_reference(text):
    """→ (book, first chapter, last chapter, v1, v2). No chapter: the whole book (chapters None)."""
    m = REF.match(text)
    if not m or not m["book"].strip():
        raise SystemExit(f"Can't read the reference “{text}”. Try “Romans”, “Romans 12”, “Romans 12-14”, "
                         f"“Romans 12:1-8” or “罗马书 12”.")
    book = find_book(m["book"].strip())
    if not m["ch"]:
        return book, None, None, None, None
    ch = int(m["ch"])
    ch2 = int(m["ch2"]) if m["ch2"] else ch
    v1 = int(m["v1"]) if m["v1"] else None
    v2 = int(m["v2"]) if m["v2"] else v1
    if v1 and ch2 != ch:
        raise SystemExit(f"“{text}”: verses can only be given within one chapter.")
    return book, ch, ch2, v1, v2


# ------------------------------------------------------------------------------------ versions
# lang: zh, en, greek or hebrew. fetch: how bible_fetch.py gets it. books: which books it has.
VERSIONS = {
    "cuv": dict(lang="zh", title="和合本 (Chinese Union Version, 1919)", label="和合本",
                fetch=("scrollmapper", "ChiUn"), books="all"),
    "web": dict(lang="en", title="World English Bible (WEB)", label="WEB", fetch=("web",), books="all"),
    "kjv": dict(lang="en", title="King James Version (KJV, 1769)", label="KJV", fetch=("scrollmapper", "KJV"), books="all"),
    "akjv": dict(lang="en", title="American King James Version (AKJV)", label="AKJV", fetch=("scrollmapper", "AKJV"), books="all"),
    "nheb": dict(lang="en", title="New Heart English Bible (NHEB)", label="NHEB", fetch=("scrollmapper", "NHEB"), books="all"),
    "asv": dict(lang="en", title="American Standard Version (ASV, 1901)", label="ASV", fetch=("scrollmapper", "ASV"), books="all"),
    "bbe": dict(lang="en", title="Bible in Basic English (BBE, 1949/1964)", label="BBE", fetch=("scrollmapper", "BBE"), books="all"),
    "ylt": dict(lang="en", title="Young's Literal Translation (YLT, 1898)", label="YLT", fetch=("scrollmapper", "YLT"), books="all"),
    "darby": dict(lang="en", title="Darby Bible (1889)", label="Darby", fetch=("scrollmapper", "Darby"), books="all"),
    "webster": dict(lang="en", title="Webster Bible (1833)", label="Webster", fetch=("scrollmapper", "Webster"), books="all"),
    "rotherham": dict(lang="en", title="Rotherham's Emphasized Bible (1902)", label="Rotherham",
                      fetch=("scrollmapper", "Rotherham"), books="all"),
    "noyes": dict(lang="en", title="Noyes Translation (1869)", label="Noyes", fetch=("scrollmapper", "Noyes"), books="all"),
    "tyndale": dict(lang="en", title="Tyndale Bible (1525/1530)", label="Tyndale", fetch=("scrollmapper", "Tyndale"), books="all"),
    "jps": dict(lang="en", title="Jewish Publication Society Old Testament (JPS, 1917)", label="JPS",
                fetch=("scrollmapper", "JPS"), books="ot"),
    "sblgnt": dict(lang="greek", title="SBL Greek New Testament (SBLGNT)", label="SBLGNT", fetch=("sblgnt",), books="nt",
                   attribution="Greek: SBL Greek New Testament, © 2010 Society of Biblical Literature and Logos "
                               "Bible Software (sblgnt.com)."),
    "tr": dict(lang="greek", title="Textus Receptus (1550/1894)", label="TR", fetch=("scrollmapper", "TR"), books="nt"),
    "byz": dict(lang="greek", title="Byzantine Textform (2013)", label="Byz", fetch=("scrollmapper", "Byz"), books="nt"),
    "wlc": dict(lang="hebrew", title="Westminster Leningrad Codex (WLC)", label="WLC", fetch=("scrollmapper", "WLC"), books="ot"),
}


def covers(version, book):
    books = VERSIONS[version]["books"]
    return books == "all" or (books == "nt") == (book >= NT_START)


# ------------------------------------------------------------------------------ source files
def source_path(version, book):
    return os.path.join(SOURCES, version, f"{book:02d}-{book_slug(book)}.json")


class MissingSource(Exception):
    def __init__(self, version, book):
        super().__init__(f"{version} {BOOKS[book - 1][0]}")
        self.version, self.book = version, book


_loaded = {}


def load(version, book):
    """{"chapters": {int: {int: text}}, "paragraphs": {int: [verses]}} for one book of one version."""
    key = (version, book)
    if key not in _loaded:
        path = source_path(version, book)
        if not os.path.exists(path):
            raise MissingSource(version, book)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _loaded[key] = {
            "chapters": {int(c): {int(v): t for v, t in vs.items()} for c, vs in data["chapters"].items()},
            "paragraphs": {int(c): vs for c, vs in data.get("paragraphs", {}).items()},
        }
    return _loaded[key]


def save(version, book, chapters, paragraphs=None):
    """Writes one book of one version to sources/, one verse per line so diffs stay small."""
    path = source_path(version, book)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["{", f'  "version": {json.dumps(version)},', f'  "book": {book},',
             f'  "name": {json.dumps(BOOKS[book - 1][0])},', '  "chapters": {']
    chapter_numbers = sorted(chapters)
    for i, c in enumerate(chapter_numbers):
        verses = chapters[c]
        lines.append(f'    "{c}": {{')
        numbers = sorted(verses)
        for j, v in enumerate(numbers):
            comma = "," if j < len(numbers) - 1 else ""
            lines.append(f'      "{v}": {json.dumps(verses[v], ensure_ascii=False)}{comma}')
        lines.append("    }" + ("," if i < len(chapter_numbers) - 1 else ""))
    lines.append("  }" + ("," if paragraphs else ""))
    if paragraphs:
        items = [f'    "{c}": {json.dumps(paragraphs[c])}' for c in sorted(paragraphs)]
        lines += ['  "paragraphs": {', ",\n".join(items), "  }"]
    lines.append("}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    _loaded.pop((version, book), None)
    return path


def available_books(version):
    folder = os.path.join(SOURCES, version)
    if not os.path.isdir(folder):
        return []
    return sorted(int(n[:2]) for n in os.listdir(folder) if re.match(r"\d\d-.*\.json$", n))


# ----------------------------------------------------------------------------------- download
def download(url, name):
    """A raw upstream file, kept in the download cache (~/.cache/chinesereader-bible)."""
    os.makedirs(DOWNLOADS, exist_ok=True)
    path = os.path.join(DOWNLOADS, name)
    if not os.path.exists(path):
        print(f"  downloading {url.rsplit('/', 1)[-1]} …", file=sys.stderr)
        with urllib.request.urlopen(url, timeout=180) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
    return path


def fetch_book(version, book):
    """Downloads (or takes from the download cache) one book of one version and cleans it.
    → (chapters {int: {int: text}}, paragraphs {int: [verses]} or {})."""
    kind = VERSIONS[version]["fetch"]
    if kind[0] == "scrollmapper":
        with open(download(SCROLLMAPPER.format(kind[1]), f"{kind[1]}.json"), encoding="utf-8") as f:
            data = json.load(f)
        entry = next((b for b in data["books"] if _book_number(b["name"]) == book), None)
        chapters = {}
        for ch in (entry or {}).get("chapters", []):
            verses = {v["verse"]: clean(version, v["text"]) for v in ch["verses"] if v["text"].strip()}
            if verses:
                chapters[ch["chapter"]] = verses
        return chapters, {}
    if kind[0] == "web":
        name = re.sub(r"[^a-z0-9]", "", BOOKS[book - 1][0].lower()).replace("songofsongs", "songofsolomon")
        with open(download(WEB.format(name), f"web-{name}.json"), encoding="utf-8") as f:
            items = json.load(f)
        chapters, paragraphs, new_paragraph = {}, {}, True
        for item in items:
            if item.get("type") in ("paragraph start", "stanza start"):
                new_paragraph = True
            if "verseNumber" not in item:
                continue
            c, v = item["chapterNumber"], item["verseNumber"]
            starts = paragraphs.setdefault(c, [])
            if new_paragraph and v not in starts:
                starts.append(v)
            new_paragraph = False
            verses = chapters.setdefault(c, {})
            verses[v] = (verses.get(v, "") + " " + item.get("value", "")).strip()
        chapters = {c: {v: re.sub(r"\s+", " ", t) for v, t in vs.items()} for c, vs in chapters.items()}
        return chapters, paragraphs
    if kind[0] == "sblgnt":
        number = book - NT_START + 61
        code = SBLGNT_CODES[book - NT_START]
        chapters = {}
        with open(download(SBLGNT.format(f"{number}-{code}"), f"sblgnt-{number}-{code}.txt"), encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                c, v = int(parts[0][2:4]), int(parts[0][4:6])
                word = re.sub(r"[⸀⸁⸂⸃⸄⸅()\[\]]", "", parts[3])        # the critical-apparatus marks
                chapters.setdefault(c, {}).setdefault(v, []).append(word)
        return {c: {v: " ".join(ws) for v, ws in vs.items()} for c, vs in chapters.items()}, {}
    raise ValueError(kind)


def clean(version, text):
    text = text.strip()
    if version == "darby":       # the Darby file runs some words together: "ofGod"
        text = re.sub(r"(?<=[a-z])(?=God\b|Lord\b|Jesus\b|Christ\b)", " ", text)
    return text
