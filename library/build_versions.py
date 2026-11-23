#!/usr/bin/env python3
"""Build the library's one-folder-per-version layout (see ReaderText/LIBRARY_REORG.md).

Reads   BibleSources (the Bible editions, in their own versification: the WLC stays Masoretic),
        workspace_islam/sources/quran/riwayat/<id>.tsv (the Qur'an readings, in their own counts),
        <lib>/search/<old-id>.tsv for what has no other source here (Naskapi, Hafs Arabic,
        romanization, Pickthall), and <lib>/bible/versions.json for names and licences
Writes  <lib>/versions/<collection>/<key>/version.json
        <lib>/versions/bible/<key>/<USFM>/<chapter>.tsv     verse \t text [\t pinyin]
        <lib>/versions/quran/<key>/<NNN>.tsv                ayah  \t text
        <lib>/versions/collections.json, <lib>/schemes/*.json, <lib>/bundles/ChineseReader.json
Curated fields in an existing version.json (coverage.omitted, notes, access) are kept on rerun.
Then run gap_analysis.py to fill coverage and write the report.

  python3 build_versions.py ~/Documents/workspace_chinese/ReaderText
"""
import json, os, sys, csv, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bible"))
import bible_pages as bp            # BibleSources' bible_sources (as bp.bs) and the Hanzi/pinyin rules
bs = bp.bs
ISLAM = os.path.expanduser(os.environ.get("WORKSPACE_ISLAM", "~/Documents/workspace_islam"))
from collections import defaultdict

BOOKS = [  # slug, USFM, English name, testament
 ("genesis","GEN","Genesis","OT"),("exodus","EXO","Exodus","OT"),("leviticus","LEV","Leviticus","OT"),
 ("numbers","NUM","Numbers","OT"),("deuteronomy","DEU","Deuteronomy","OT"),("joshua","JOS","Joshua","OT"),
 ("judges","JDG","Judges","OT"),("ruth","RUT","Ruth","OT"),("1-samuel","1SA","1 Samuel","OT"),
 ("2-samuel","2SA","2 Samuel","OT"),("1-kings","1KI","1 Kings","OT"),("2-kings","2KI","2 Kings","OT"),
 ("1-chronicles","1CH","1 Chronicles","OT"),("2-chronicles","2CH","2 Chronicles","OT"),("ezra","EZR","Ezra","OT"),
 ("nehemiah","NEH","Nehemiah","OT"),("esther","EST","Esther","OT"),("job","JOB","Job","OT"),
 ("psalms","PSA","Psalms","OT"),("proverbs","PRO","Proverbs","OT"),("ecclesiastes","ECC","Ecclesiastes","OT"),
 ("song-of-songs","SNG","Song of Songs","OT"),("isaiah","ISA","Isaiah","OT"),("jeremiah","JER","Jeremiah","OT"),
 ("lamentations","LAM","Lamentations","OT"),("ezekiel","EZK","Ezekiel","OT"),("daniel","DAN","Daniel","OT"),
 ("hosea","HOS","Hosea","OT"),("joel","JOL","Joel","OT"),("amos","AMO","Amos","OT"),("obadiah","OBA","Obadiah","OT"),
 ("jonah","JON","Jonah","OT"),("micah","MIC","Micah","OT"),("nahum","NAM","Nahum","OT"),("habakkuk","HAB","Habakkuk","OT"),
 ("zephaniah","ZEP","Zephaniah","OT"),("haggai","HAG","Haggai","OT"),("zechariah","ZEC","Zechariah","OT"),
 ("malachi","MAL","Malachi","OT"),
 ("matthew","MAT","Matthew","NT"),("mark","MRK","Mark","NT"),("luke","LUK","Luke","NT"),("john","JHN","John","NT"),
 ("acts","ACT","Acts","NT"),("romans","ROM","Romans","NT"),("1-corinthians","1CO","1 Corinthians","NT"),
 ("2-corinthians","2CO","2 Corinthians","NT"),("galatians","GAL","Galatians","NT"),("ephesians","EPH","Ephesians","NT"),
 ("philippians","PHP","Philippians","NT"),("colossians","COL","Colossians","NT"),
 ("1-thessalonians","1TH","1 Thessalonians","NT"),("2-thessalonians","2TH","2 Thessalonians","NT"),
 ("1-timothy","1TI","1 Timothy","NT"),("2-timothy","2TI","2 Timothy","NT"),("titus","TIT","Titus","NT"),
 ("philemon","PHM","Philemon","NT"),("hebrews","HEB","Hebrews","NT"),("james","JAS","James","NT"),
 ("1-peter","1PE","1 Peter","NT"),("2-peter","2PE","2 Peter","NT"),("1-john","1JN","1 John","NT"),
 ("2-john","2JN","2 John","NT"),("3-john","3JN","3 John","NT"),("jude","JUD","Jude","NT"),("revelation","REV","Revelation","NT"),
]
SLUG2USFM = {b[0]: b[1] for b in BOOKS}
OT = {b[1] for b in BOOKS if b[3] == "OT"}

# new key -> (BibleSources version, legacy id in versions.json); None = from search/<legacy>.tsv.
# A tuple of BibleSources versions: the first one there (downloaded first, then the "-input" import).
BIBLE = {
 "en-kjv": ("kjv", "kjv"), "en-web": ("web", "web"), "en-bbe": ("bbe", "bbe"),
 "en-asv": (("asv", "asv-input"), "asv"), "en-ylt": (("ylt", "ylt-input"), "ylt"),
 "en-darby": (("darby", "darby-input"), "darby"), "en-webster": (("wb", "webster", "wbt", "wb-input"), "webster"),
 "en-akjv": (("akjv", "akjv-input"), "akjv"),
 "zh-cuv-s": ("cuv", "simplified"), "zh-cuv-t": ("cuv", "traditional"),
 "hbo-wlc": ("wlc", "original"), "grc-sblgnt": ("sblgnt", "original"), "grc-tr": ("tr", "original"),
 "ko-krv": ("krv", "krv"), "th-kjv": ("thkjv", "thkjv"), "vi-1934": ("vietnamese", "vietnamese"),
 "fr-martin": ("martin", "martin"), "de-luther1912": ("luther1912", "luther1912"),
 "nsk-naskapi": (None, "naskapi"),
}
NAMES = {"hbo-wlc": ("Westminster Leningrad Codex (WLC)", "WLC", "hbo", "Public domain", "masoretic"),
         "grc-sblgnt": ("SBL Greek New Testament (SBLGNT)", "SBLGNT", "grc", "CC BY 4.0", "kjv"),
         "grc-tr": ("Textus Receptus (1550/1894)", "TR", "grc", "Public domain", "kjv"),
         "en-asv": ("American Standard Version (ASV, 1901)", "ASV", "en", "Public domain", "kjv"),
         "en-ylt": ("Young's Literal Translation (YLT, 1898)", "YLT", "en", "Public domain", "kjv"),
         "en-darby": ("Darby Bible (1890)", "Darby", "en", "Public domain", "kjv"),
         "en-webster": ("Webster's Bible (1833)", "Webster", "en", "Public domain", "kjv"),
         "en-akjv": ("American King James Version (AKJV)", "AKJV", "en", "Public domain", "kjv")}
QURAN = {
 "quran-arabic": "ar-hafs", "quran-romanization": "ar-latn-hafs",
 "quran-riwaya-shubah": "ar-shubah", "quran-riwaya-warsh": "ar-warsh", "quran-riwaya-qalun": "ar-qalun",
 "quran-riwaya-duri": "ar-duri", "quran-riwaya-susi": "ar-susi", "quran-riwaya-bazzi": "ar-bazzi",
 "quran-riwaya-qunbul": "ar-qunbul", "pickthall": "en-pickthall", "sahih-international": "en-sahih",
}
QURAN_SCHEME = {"shubah": "kufan", "warsh": "madinan-2", "qalun": "madinan-2", "duri": "basran",
                "susi": "basran", "bazzi": "makkan", "qunbul": "makkan"}
# the app's version ids (bible/versions.json) a key stands for; the CUV simplified carries the pinyin
LEGACY = {"zh-cuv-s": ["simplified", "pinyin"]}
RESTRICTED = {"nsk-naskapi": "permission", "th-kjv": "nc-nd", "en-sahih": "private"}
SCRIPT = {"zh-Hans": "Hans", "zh-Hant": "Hant", "en": "Latn", "ko": "Hang", "th": "Thai", "vi": "Latn",
          "fr": "Latn", "de": "Latn", "nsk": "Cans", "ar": "Arab", "ar-Latn": "Latn", "hbo": "Hebr", "grc": "Grek"}

def read_tsv(path):
    rows = defaultdict(dict)  # page-key -> {verse: text}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(r) >= 3:
                rows[r[0]][r[1]] = r[2]
    return rows

def split_key(k):
    slug, _, ch = k.rpartition("-")
    return SLUG2USFM.get(slug), ch

def vsort(v):
    d = "".join(c for c in v if c.isdigit())
    return (int(d) if d else 0, v)

def merge_meta(path, meta):
    if os.path.exists(path):
        old = json.load(open(path, encoding="utf-8"))
        for keep in ("access", "notes"):
            if keep in old: meta[keep] = old[keep]
        if "coverage" in old: meta["coverage"] = old["coverage"]
    return meta

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2); f.write("\n")

def clean(text):
    return re.sub(r"[\t\r\n]+", " ", str(text)).strip()


def resolve_source(src):
    """A BibleSources version name as given, or the first of a tuple that has any book; "" when
    none of them does."""
    if src is None or isinstance(src, str):
        return src
    for name in src:
        for n in range(1, len(BOOKS) + 1):
            try:
                if os.path.exists(bs.source_path(name, n)):
                    return name
            except Exception:
                break                               # not a version BibleSources knows
    return ""


def bible_chapters(lib, key, src, oid, cache):
    """{(USFM, chapter): [[verse, text(, pinyin)], …]} for one version."""
    out = {}
    if src is None:                              # no source here: the search file (Naskapi)
        path = f"{lib}/search/{oid}.tsv"
        if not os.path.exists(path): return out
        for pk, verses in read_tsv(path).items():
            usfm, ch = split_key(pk)
            if usfm: out[(usfm, ch)] = [[v, verses[v]] for v in sorted(verses, key=vsort)]
        return out
    for n, (slug, usfm, _, _) in enumerate(BOOKS, 1):
        if not os.path.exists(bs.source_path(src, n)):
            if src == "cuv" and os.path.exists(bs.source_path("cut", n)):
                pass                                 # the builder falls back to the traditional input
            else:
                continue
        for ch in sorted(bs.load(src if os.path.exists(bs.source_path(src, n)) else "cut", n)["chapters"]):
            if key.startswith("zh-cuv"):
                rows = cache.get((usfm, ch))
                if rows is None:
                    rows = cache[(usfm, ch)] = chinese_rows(n, ch)
                out[(usfm, str(ch))] = [[v, s if key == "zh-cuv-s" else t, p] for v, s, t, p in rows]
            else:
                text = bp.version_text(src, n, ch)
                out[(usfm, str(ch))] = [[str(v), text[v]] for v in sorted(text)]
    return out


_KIT = None

def chinese_rows(book, chapter):
    """[(verse, simplified spaced, traditional spaced, pinyin)], made by the same language kit as the
    passage pages (CUV small-print notes such as （有古卷…） left out, as on the pages)."""
    global _KIT
    if _KIT is None:
        from languages.chinese import ChineseKit
        _KIT = ChineseKit(script="both")
    rows = _KIT.verses(book, chapter)
    return [(str(v), r[0], r[2], r[1]) for v, r in sorted(rows.items())]


def main(lib):
    old = {v["id"]: v for v in json.load(open(f"{lib}/bible/versions.json", encoding="utf-8"))["versions"]}
    out = f"{lib}/versions"; written = []; legacy_of = {}
    pinyin = {}

    for key, (src, oid) in BIBLE.items():
        src = resolve_source(src)
        if src == "": print("skip (not in BibleSources):", key); continue
        chapters = bible_chapters(lib, key, src, oid, pinyin)
        if not chapters: print("skip (no data):", key); continue
        n = 0
        for (usfm, ch), rows in chapters.items():
            os.makedirs(f"{out}/bible/{key}/{usfm}", exist_ok=True)
            with open(f"{out}/bible/{key}/{usfm}/{ch}.tsv", "w", encoding="utf-8") as f:
                for row in rows:
                    f.write("\t".join(clean(c) for c in row) + "\n"); n += 1
        o = old.get(oid, {})
        name, short, lang, lic, numbering = NAMES.get(key, (o.get("title"), o.get("short"), o.get("language", ""),
                                                            o.get("license"), "kjv"))
        meta = {"key": key, "collection": "bible", "name": name, "short": short,
                "language": lang, "script": SCRIPT.get(lang, ""), "kind": o.get("kind"),
                "license": lic, "numbering": numbering, "levels": ["book", "chapter", "verse"],
                "columns": ["verse", "text"] + (["pinyin"] if key.startswith("zh-cuv") else []),
                "source": src or f"search/{oid}.tsv", "legacyID": oid, "verses": n,
                "coverage": {"books": {}, "omitted": [], "additional": []}}
        if key in RESTRICTED: meta["access"] = RESTRICTED[key]
        write_json(f"{out}/bible/{key}/version.json", merge_meta(f"{out}/bible/{key}/version.json", meta))
        written.append(("bible", key, n)); legacy_of[key] = oid

    for oid, key in QURAN.items():
        riwaya = oid.replace("quran-riwaya-", "") if oid.startswith("quran-riwaya-") else None
        src = f"{ISLAM}/sources/quran/riwayat/{riwaya}.tsv" if riwaya else f"{lib}/search/{oid}.tsv"
        if not os.path.exists(src): print("skip (no data):", oid); continue
        by_surah = defaultdict(list)
        with open(src, encoding="utf-8", newline="") as f:
            for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
                if riwaya:     # riwaya surah ayah hafs_start hafs_end starts_mid text
                    if r[0] != riwaya: continue
                    by_surah[f"{int(r[1]):03d}"].append([r[2], r[6], r[3], r[4]])
                elif len(r) >= 3:
                    by_surah[r[0].split("-")[0]].append([r[1], r[2]])
        n = 0
        os.makedirs(f"{out}/quran/{key}", exist_ok=True)
        for sur, rows in by_surah.items():
            with open(f"{out}/quran/{key}/{sur}.tsv", "w", encoding="utf-8") as f:
                for row in sorted(rows, key=lambda r: vsort(r[0])):
                    f.write("\t".join(clean(c) for c in row) + "\n"); n += 1
        o = old.get(oid, {}); lang = o.get("language", "")
        scheme = QURAN_SCHEME.get(riwaya or "", "kufan")
        meta = {"key": key, "collection": "quran", "name": o.get("title"), "short": o.get("short"),
                "language": lang, "script": SCRIPT.get(lang, ""), "kind": o.get("kind"), "license": o.get("license"),
                "numbering": scheme, "levels": ["surah", "ayah"],
                "columns": ["ayah", "text"] + (["hafsStart", "hafsEnd"] if riwaya else []),
                "source": os.path.relpath(src, os.path.dirname(lib)) if not riwaya else f"workspace_islam/sources/quran/riwayat/{riwaya}.tsv",
                "legacyID": oid, "verses": n, "coverage": {"books": {}, "omitted": [], "additional": []}}
        if key in RESTRICTED: meta["access"] = RESTRICTED[key]
        write_json(f"{out}/quran/{key}/version.json", merge_meta(f"{out}/quran/{key}/version.json", meta))
        written.append(("quran", key, n)); legacy_of[key] = oid

    write_json(f"{out}/collections.json", {
      "collections": [
        {"id": "bible", "name": "Bible", "levels": ["book", "chapter", "verse"], "reference": "kjv",
         "books": [{"code": u, "slug": s, "name": nm, "testament": t} for s, u, nm, t in BOOKS]},
        {"id": "quran", "name": "Qur'an", "levels": ["surah", "ayah"], "reference": "kufan",
         "books": [{"code": f"{i:03d}"} for i in range(1, 115)]},
        {"id": "hadith", "name": "Hadith", "levels": ["book", "section", "number"], "reference": None, "books": []},
        {"id": "documents", "name": "Other Documents", "levels": ["page"], "reference": None, "books": []}],
      "versions": [{"collection": c, "key": k, "legacyIDs": LEGACY.get(k, [legacy_of[k]])} for c, k, _ in written]})
    write_json(f"{lib}/bundles/ChineseReader.json", {
      "app": "ChineseReader",
      "required": ["en-kjv", "zh-cuv-s", "zh-cuv-t"],
      "_about": "required: always in the app and its default view; default: in the default view; "
                "offered: listed for adding; hidden: never listed, added or searched",
      "default":  ["en-kjv", "zh-cuv-s", "zh-cuv-t", "hbo-wlc", "grc-sblgnt"],
      "offered":  [k for _, k, _ in written if k not in ("en-kjv", "zh-cuv-s", "zh-cuv-t", "hbo-wlc", "grc-sblgnt", "en-sahih")],
      "hidden":   ["en-sahih"]})
    for c, k, n in written: print(f"{c:6} {k:16} {n:6} verses")

if __name__ == "__main__":
    main(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Documents/workspace_chinese/ReaderText"))
