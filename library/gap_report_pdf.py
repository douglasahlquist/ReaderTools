#!/usr/bin/env python3
"""Gap report PDFs from versions/gap-report.json (run gap_analysis.py first):

  documents/reference/bible-gap-report.pdf
  documents/reference/islamic-texts-gap-report.pdf

  python3 gap_report_pdf.py ~/Documents/workspace_chinese/ReaderText [--islam ~/Documents/workspace_islam]
"""
import argparse, csv, glob, json, os, sys
from collections import Counter, defaultdict
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from versification import SHIFTS

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/Library/Fonts", os.path.expanduser("~/Library/Fonts"),
             "/System/Library/Fonts/Supplemental"]

def register_fonts():
    for name, file in [("Body", "DejaVuSans.ttf"), ("Body-Bold", "DejaVuSans-Bold.ttf"),
                       ("Body-Italic", "DejaVuSans-Oblique.ttf")]:
        path = next((os.path.join(d, file) for d in FONT_DIRS if os.path.exists(os.path.join(d, file))), None)
        if not path: sys.exit(f"needs {file} (DejaVu fonts): brew install --cask font-dejavu")
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")

INK, MUTED, RULE, TINT = colors.HexColor("#1f2933"), colors.HexColor("#52606d"), colors.HexColor("#cbd2d9"), colors.HexColor("#f0f4f8")
ACCENT = colors.HexColor("#2a4d69")
S = {}
def styles():
    S["title"] = ParagraphStyle("title", fontName="Body-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=4)
    S["sub"] = ParagraphStyle("sub", fontName="Body", fontSize=10, leading=14, textColor=MUTED, spaceAfter=14)
    S["h1"] = ParagraphStyle("h1", fontName="Body-Bold", fontSize=13.5, leading=17, textColor=ACCENT, spaceBefore=14, spaceAfter=6)
    S["h2"] = ParagraphStyle("h2", fontName="Body-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=10, spaceAfter=4)
    S["p"] = ParagraphStyle("p", fontName="Body", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=6, alignment=TA_LEFT)
    S["li"] = ParagraphStyle("li", parent=S["p"], leftIndent=12, bulletIndent=2, spaceAfter=3)
    S["cell"] = ParagraphStyle("cell", fontName="Body", fontSize=8.3, leading=10.5, textColor=INK)
    S["cellb"] = ParagraphStyle("cellb", parent=S["cell"], fontName="Body-Bold")
    S["small"] = ParagraphStyle("small", fontName="Body", fontSize=8, leading=11, textColor=MUTED)

def P(t, s="p"): return Paragraph(t, S[s])
def bullets(items): return [Paragraph(t, S["li"], bulletText="•") for t in items]

def table(rows, widths, header=True, align_right=()):
    data = [[c if not isinstance(c, str) else Paragraph(c, S["cellb" if header and i == 0 else "cell"]) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header: st += [("BACKGROUND", (0, 0), (-1, 0), TINT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT)]
    t.setStyle(TableStyle(st)); return t

def footer(title):
    def draw(canvas, doc):
        canvas.saveState(); canvas.setFont("Body", 7.5); canvas.setFillColor(MUTED)
        canvas.drawString(0.75 * inch, 0.5 * inch, f"ReaderText · {title}")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()
    return draw

def build(path, title, story):
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.75 * inch, title=title, author="Douglas Ahlquist",
                            subject="ReaderText library gap analysis")
    doc.build(story, onFirstPage=footer(title), onLaterPages=footer(title))

W = letter[0] - 1.5 * inch

def fmt_refs(refs, limit=None):
    """GEN.31.55 → GEN 31:55; QURAN 001.1 → 1:1"""
    out = []
    import re as _re
    key = lambda r: [int(x) if x.isdigit() else x for x in _re.split(r"[.:]", r)]
    refs = sorted(refs, key=key)
    for r in refs:
        parts = r.split(".")
        out.append(f"{parts[0]} {parts[1]}:{parts[2]}" if len(parts) == 3 else
                   f"{int(parts[0])}:{parts[1]}" if len(parts) == 2 and parts[0].isdigit() else r)
    if limit and len(out) > limit: out = out[:limit] + [f"… and {len(refs) - limit} more"]
    return ", ".join(out)

LATIN = {"zh-cuv-s": ("CUV Simplified", "Chinese Union Version (1919), simplified"),
         "zh-cuv-t": ("CUV Traditional", "Chinese Union Version (1919), traditional"),
         "ko-krv": ("Korean (KRV)", "Korean Revised Version (1961)")}

def latin(v):
    """Short name and name without CJK script (the PDF font has none)."""
    if v["key"] in LATIN: return LATIN[v["key"]]
    return v["short"] or v["name"], v["name"]

def by_reason(d):
    g = defaultdict(list)
    for r, why in d.items(): g[why or "—"].append(r)
    return g

# ------------------------------------------------------------------------------------------ Bible
def bible_pdf(rep, out):
    vs = [v for v in rep["versions"] if v["collection"] == "bible"]
    order = ["en-kjv", "zh-cuv-s", "zh-cuv-t", "hbo-wlc", "grc-sblgnt", "grc-tr", "en-web", "en-bbe", "ko-krv",
             "th-kjv", "vi-1934", "fr-martin", "de-luther1912", "nsk-naskapi"]
    vs.sort(key=lambda v: order.index(v["key"]) if v["key"] in order else 99)
    ref = rep["reference"]
    st = [P("Bible Versions — Gap Report", "title"),
          P(f"ReaderText library · one folder per version · generated {rep['generated']}", "sub"),
          P("What this report is", "h1"),
          P("Every Bible version in the library is measured against one reference numbering, the King James "
            f"Version's ({ref['bible']:,} verses in 66 books). For each version the gap analysis records which "
            "books it contains (its <b>coverage</b>), and sorts every difference from the reference into one of "
            "three kinds:"),
          *bullets(["<b>Omitted in this edition</b> — the edition leaves the verse out, or joins it to a neighbour, on "
                    "purpose. Listed with the reason in the version's <i>version.json</i>; the app says "
                    "“omitted in this edition”.",
                    "<b>Possibly a data error</b> — missing inside the version's coverage with no reason recorded. "
                    "The app says “missing — possibly a data error” until it is fixed or explained.",
                    "<b>Additional</b> — verses beyond the reference numbering (a psalm title counted as verse 1, "
                    "a verse divided in two)."]),
          P("A book a version does not contain is outside its coverage, not a gap: the Naskapi Old Testament has "
            "Genesis, Exodus and Psalms only, and nothing is reported for the other 36 books. Notes can be attached "
            "to any gap, per version."),
          P("Summary", "h1")]
    rows = [["Version", "Key", "Verses", "Books", "Numbering", "Omitted", "Additional", "Possible errors"]]
    for v in vs:
        rows.append([latin(v)[0], v["key"], f"{v['verses']:,}", str(v["books"]), v["numbering"],
                     str(len(v["omitted"])) if v["omitted"] else "—", str(len(v["additional"])) if v["additional"] else "—",
                     f"<b>{len(v['missing'])}</b>" if v["missing"] else "—"])
    st += [table(rows, [W * .19, W * .15, W * .10, W * .08, W * .12, W * .11, W * .12, W * .13]),
           Spacer(1, 6),
           P(f"Every verse of every whole-Bible edition is now accounted for except in three versions: Martin (French), "
             f"the Korean Revised Version and Naskapi. Their {sum(len(v['missing']) for v in vs)} remaining verses are "
             "listed under each version below.", "small"),
           P("Fixed in this pass", "h1"),
           *bullets([
             "<b>Malachi 4 restored everywhere.</b> The old passage pages took their chapter list from the Hebrew, "
             "where Malachi ends at 3:24, so Malachi 4 (six verses) was never built in any version. The version folders "
             "are now built straight from the source texts, so every version has the chapters it really has.",
             "<b>John 7:53 restored</b> in every edition that has it. The Chinese Union Version joins it to 8:1 "
             "(“Then each went home, but Jesus went to the Mount of Olives”), now recorded as joined, not missing.",
             f"<b>The Hebrew keeps its own numbering.</b> The WLC now carries all {ref['masoretic']:,} Masoretic verses "
             f"in Hebrew chapter and verse numbers, with a map to the KJV ({ref['masoreticShifts']:,} verses renumbered) "
             "in <i>schemes/masoretic.json</i>. Before, 134 Hebrew verses were missing or misplaced on English-numbered pages.",
             "<b>Chinese word spacing kept.</b> The CUV is stored with the same word spacing and pinyin as the passage "
             "pages, so word-by-word speech and the reading underline keep working.",
             "<b>Textus Receptus</b> added as its own version (grc-tr, John and Romans so far)."]),
           P("How the Hebrew lines up with the English", "h1"),
           P("Outside the Psalms, these are the places where Hebrew and English chapter or verse numbers differ. "
             "In the Psalms, the Hebrew counts most titles as verse 1 (or verses 1–2), so the "
             "whole psalm is one or two higher: Psalm 3:1 in English is 3:2 in Hebrew."),
           table([["English (KJV)", "Hebrew (WLC)"]] +
                 [[f"{b} {kc}:{k1}" + (f"–{k2}" if k2 != k1 else ""),
                   f"{b} {hc}:{h1}" + (f"–{h1 + k2 - k1}" if k2 != k1 else "")] for b, kc, k1, k2, hc, h1 in SHIFTS]
                 + [["NEH 7:68", "not in the Masoretic text"]], [W * .3, W * .3]),
           PageBreak(), P("Version by version", "h1")]
    for v in vs:
        block = [P(f"{latin(v)[1]} <font color='#52606d'>· {v['key']}</font>", "h2"),
                 P(f"{v['verses']:,} verses · {v['books']} books · numbering: {v['numbering']} · licence: {v['license']}"
                   + (f" · access: <b>{v['access']}</b>" if v.get("access") else ""), "small")]
        if v["partial"]:
            block.append(P("Partial books: " + "; ".join(f"{b} {r}" for b, r in v["partial"].items())))
        for why, refs in by_reason(v["omitted"]).items():
            block.append(P(f"<b>Omitted/joined</b> ({len(refs)}) — {why}: {fmt_refs(refs)}"))
        for why, refs in by_reason(v["additional"]).items():
            block.append(P(f"<b>Additional</b> ({len(refs)}) — {why}: {fmt_refs(refs, 24)}"))
        if v["missing"]:
            block.append(P(f"<b><font color='#a61b1b'>Possibly data errors ({len(v['missing'])})</font></b>: {fmt_refs(v['missing'])}"))
        if not (v["omitted"] or v["additional"] or v["missing"] or v["partial"]):
            block.append(P("Complete against the reference — nothing to report."))
        st.append(KeepTogether(block))
    st += [P("What to do next", "h1"), *bullets([
        "<b>Martin (1744)</b>: 31 verses lost at chapter ends where French numbering follows the Hebrew (Numbers 12, "
        "Job 38 and 41, Ezekiel 20, Jonah 1 …) — the following chapter is not longer, so the source dropped them. "
        "Re-source from a complete Martin text.",
        "<b>Korean Revised Version</b>: the New Testament verses printed as “(eopseum)”, ‘none’, are recorded as omitted — check against a "
        "printed copy. Seven remain (Psalm 72:20, Isaiah 30:2 and 48:2, Jeremiah 21:2, Ezekiel 24:5, Acts 15:26, "
        "Romans 9:2): probably joined verses in the source.",
        "<b>Naskapi</b>: Genesis 25:8 and 25:15, Psalm 134:1, John 7:53 and Colossians 1:2 — check against the "
        "Naskapi corpus in workspace_naskapi.",
        "<b>ASV</b> and <b>Sahih International</b> have no data in the library yet.",
        "The old combined passage pages still lack Malachi 4; they are replaced once the app reads the version folders."]),
        P("Regenerate", "h1"),
        P("From ChineseReaderTools/library: <i>build_versions.py</i> (version folders), <i>gap_analysis.py</i> "
          "(coverage, schemes, versions/gap-report.md and .json), then <i>gap_report_pdf.py</i> (these PDFs).", "small")]
    build(out, "Bible Versions — Gap Report", st)

# ---------------------------------------------------------------------------------------- Islamic
def islam_pdf(rep, out, islam):
    vs = [v for v in rep["versions"] if v["collection"] == "quran"]
    order = ["ar-hafs", "ar-shubah", "ar-warsh", "ar-qalun", "ar-duri", "ar-susi", "ar-bazzi", "ar-qunbul",
             "ar-latn-hafs", "en-pickthall"]
    vs.sort(key=lambda v: order.index(v["key"]) if v["key"] in order else 99)
    expected = {"kufan": 6236, "madinan-2": 6214, "basran": 6217, "makkan": 6220}
    st = [P("Islamic Texts — Gap Report", "title"),
          P(f"ReaderText library · the Qur'an and the hadith collections · generated {rep['generated']}", "sub"),
          P("What this report is", "h1"),
          P("The Qur'an's text does not vary in content between its canonical readings (riwayat), but the readings "
            "divide it into verses differently, so each has its own verse count. Each Qur'an version in the library "
            "keeps its own numbering, and is checked two ways: against its own count, and against the Hafs (Kufan) "
            "reference of 6,236 verses — every Hafs verse must fall inside some verse of the reading."),
          P("Qur'an — summary", "h1")]
    rows = [["Version", "Key", "Count", "Expected", "Verses", "Hafs verses covered", "Result"]]
    for v in vs:
        exp = expected.get(v["numbering"])
        ok = v["verses"] == exp and not v["missing"]
        rows.append([v["short"] or v["name"], v["key"], v["numbering"], f"{exp:,}" if exp else "—", f"{v['verses']:,}",
                     "all 6,236" if not v["missing"] else f"{6236 - len(v['missing']):,}",
                     "complete" if ok else f"<b>{len(v['missing'])} to check</b>"])
    st += [table(rows, [W * .2, W * .15, W * .12, W * .11, W * .1, W * .17, W * .15]), Spacer(1, 6),
           P("Hafs, Shuʿbah and the eight-reading alignment all check out; romanization and Pickthall follow the "
             "Hafs numbering exactly.", "small"),
           P("Fixed in this pass", "h1"),
           *bullets(["<b>The six non-Kufan readings were 54–64 verses short.</b> The search index was keyed by the "
                     "Hafs verse, so where two verses of a reading fall inside one Hafs verse, one overwrote the other. "
                     "The version folders are now built from the riwayat source files in each reading's own numbering, "
                     "and every count is exact: Warsh and Qālūn 6,214, al-Dūrī and al-Sūsī 6,217, al-Bazzī and Qunbul 6,220.",
                     "Each reading's files carry <i>hafsStart</i> and <i>hafsEnd</i> columns, so the app can line any "
                     "verse up with the Hafs verse (or verses) it covers."]),
           P("Where the readings divide verses differently", "h1"),
           P("Counted from the alignment (numbering_differences.tsv). A verse <i>covers more than one</i> Hafs verse "
             "when the reading joins them; it <i>starts inside</i> a Hafs verse when the reading divides one.")]
    diff = Counter()
    path = f"{islam}/sources/quran/riwayat/numbering_differences.tsv"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"): diff[(r["riwaya"], r["kind"])] += 1
    names = {v["key"].replace("ar-", ""): v["short"] for v in vs}
    rows = [["Reading", "Count", "Joins Hafs verses", "Divides a Hafs verse"]]
    for k in ("warsh", "qalun", "duri", "susi", "bazzi", "qunbul"):
        v = next((x for x in vs if x["key"] == f"ar-{k}"), None)
        if v: rows.append([names.get(k, k), v["numbering"], str(diff[(k, "covers more than one Hafs verse")]),
                           str(diff[(k, "starts inside a Hafs verse")])])
    st += [table(rows, [W * .3, W * .2, W * .25, W * .25]), Spacer(1, 4),
           P("Al-Fatihah is the best-known case: the Madinan and Basran counts do not number the basmala as 1:1, and "
             "divide Hafs 1:7 in two. That is recorded for those four readings as “not counted as a verse in this "
             "count”, not as a gap.", "small"),
           P("Qur'an — version by version", "h1")]
    for v in vs:
        block = [P(f"{v['name']} <font color='#52606d'>· {v['key']}</font>", "h2"),
                 P(f"{v['verses']:,} verses · numbering: {v['numbering']} · licence: {v['license']}", "small")]
        for why, refs in by_reason(v["omitted"]).items():
            block.append(P(f"<b>Not numbered</b> — {why}: {fmt_refs(refs)}"))
        if v["missing"]: block.append(P(f"<b><font color='#a61b1b'>To check</font></b>: {fmt_refs(v['missing'], 40)}"))
        if not (v["omitted"] or v["missing"]): block.append(P("Complete — nothing to report."))
        st.append(KeepTogether(block))
    st += [P("Sahih International is held privately (© Saheeh International, permission required) and is hidden in the "
             "ChineseReader bundle; it is not in the public library.", "small"), PageBreak()]

    # hadith
    csv.field_size_limit(10 ** 9)
    st += [P("Hadith collections", "h1"),
           P("The hadith are downloaded (fawazahmed0/hadith-api, released as public domain under The Unlicense) into "
             "workspace_islam/sources/hadith, with Arabic (with and without diacritics) and English side by side. "
             "They are not in the library's version folders yet. Each collection is numbered on its own; the "
             "reference here is the hadith-api numbering, which follows sunnah.com, with book and number-in-book kept "
             "for pointers of the form <i>hadith-muslim · book · section · number</i>.")]
    rows = [["Collection", "Hadith", "Numbers", "Books", "Sub-numbers (n.2)", "No Arabic", "No English", "Graded"]]
    notes = []
    for f in sorted(glob.glob(f"{islam}/sources/hadith/tsv/*.tsv")):
        rs = list(csv.DictReader(open(f, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))
        name = os.path.basename(f)[:-4]
        ints = sorted({int(float(r["hadith_number"])) for r in rs if r["hadith_number"]})
        gaps = [n for n in range(1, ints[-1] + 1) if n not in set(ints)] if ints else []
        frac = [r["hadith_number"] for r in rs if "." in r["hadith_number"]]
        no_ara = [r["hadith_number"] for r in rs if not r["ara"].strip()]
        no_eng = [r["hadith_number"] for r in rs if not r["eng"].strip()]
        graded = sum(1 for r in rs if r["grades"].strip())
        rows.append([name, f"{len(rs):,}", f"1–{ints[-1]:,}" + (f" ({len(gaps)} gaps)" if gaps else ""),
                     str(len({r['book'] for r in rs})), str(len(frac)) if frac else "—",
                     f"<b>{len(no_ara)}</b>" if no_ara else "—", f"<b>{len(no_eng)}</b>" if no_eng else "—",
                     f"{graded:,}" if graded else "—"])
        if no_ara or no_eng:
            short = lambda xs: ", ".join(xs[:12]) + (f" … and {len(xs) - 12} more" if len(xs) > 12 else "") or "—"
            notes.append(f"<b>{name}</b>: no Arabic at {short(no_ara)}; no English at {short(no_eng)}")
    st += [table(rows, [W * .14, W * .1, W * .16, W * .08, W * .14, W * .12, W * .12, W * .14]), Spacer(1, 6),
           P("Every collection runs from 1 without a missing number. <i>Sub-numbers</i> are extra entries a source "
             "numbers 402.2, 402.3 … (a second chain of narration, or a hadith split in two); they are additional, "
             "not gaps.", "small"),
           P("Entries with no text", "h2"), *bullets(notes),
           P("Most empty entries are chapter headings or chain-only entries that the source keeps as numbered rows "
             "(Sahih Muslim's 203 include its Introduction). The 344 Muslim entries without an Arabic number are its "
             "sub-narrations, which Muslim's own numbering does not count separately.", "small"),
           P("What to do next", "h1"), *bullets([
             "Rebuild the search index from the version folders, so the six non-Kufan readings are searchable in full.",
             "Add the hadith as a collection (versions/hadith/<key>/, with book · section · number pointers), then "
             "run the gap analysis on them with each collection's own numbering as its reference.",
             "Decide which hadith collections the ChineseReader bundle offers, and whether grades are shown.",
             "Review the generated romanization (slips such as “Talllahi”)."]),
           P("Regenerate", "h1"),
           P("From ChineseReaderTools/library: build_versions.py, gap_analysis.py, then gap_report_pdf.py.", "small")]
    build(out, "Islamic Texts — Gap Report", st)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("library", nargs="?", default="~/Documents/workspace_chinese/ReaderText")
    ap.add_argument("--islam", default=os.environ.get("WORKSPACE_ISLAM", "~/Documents/workspace_islam"))
    a = ap.parse_args()
    lib, islam = os.path.expanduser(a.library), os.path.expanduser(a.islam)
    register_fonts(); styles()
    rep = json.load(open(f"{lib}/versions/gap-report.json", encoding="utf-8"))
    os.makedirs(f"{lib}/documents/reference", exist_ok=True)
    bible_pdf(rep, f"{lib}/documents/reference/bible-gap-report.pdf")
    islam_pdf(rep, f"{lib}/documents/reference/islamic-texts-gap-report.pdf", islam)
    print("wrote documents/reference/bible-gap-report.pdf and islamic-texts-gap-report.pdf")

if __name__ == "__main__":
    main()
