#!/usr/bin/env python3
"""Gap analysis: measure each version against its collection's reference scheme.

Bible: the KJV versification (schemes/kjv.json, 31,102 verses). A Masoretic-numbered version
(hbo-wlc) is read through versification.py's map (schemes/masoretic.json).
Qur'an: the Hafs/Kufan count (schemes/kufan.json, 6,236). A reading with its own count is checked
against that count's total and through its Hafs columns (every Hafs verse should be covered).

Fills each version.json coverage: books {code: "all" | "1-3,5"}, additional [...], notes {ref: why};
keeps the curated omitted list (plus SEED below). Writes versions/gap-report.md and .json.
A verse inside coverage that is missing and not omitted = "possibly a data error".

  python3 gap_analysis.py ~/Documents/workspace_chinese/ReaderText
"""
import json, os, sys, glob
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from versification import kjv_to_masoretic, JOINED

QURAN_TOTALS = {"kufan": 6236, "madinan-2": 6214, "basran": 6217, "makkan": 6220}
# what an edition leaves out or joins on purpose: {key: {ref: reason}} (more can go in version.json)
CRITICAL_TEXT = "Not in the critical Greek text (kept in the KJV from the Textus Receptus)"
SEED = {
  "grc-sblgnt": {**{r: CRITICAL_TEXT for r in ["MAT.17.21", "MAT.18.11", "MAT.23.14", "MRK.7.16", "MRK.9.44",
       "MRK.9.46", "MRK.11.26", "MRK.15.28", "LUK.17.36", "LUK.23.17", "JHN.5.4", "ACT.8.37", "ACT.15.34",
       "ACT.24.7", "ACT.28.29", "ROM.16.24"]},
     **{r: "Not in the critical Greek text (John 7:53–8:11)" for r in ["JHN.7.53"] + [f"JHN.8.{v}" for v in range(1, 12)]},
     "ACT.19.41": "Joined to 19:40 in the Greek numbering", "2CO.13.14": "Numbered 13:13 in the Greek",
     "ROM.16.25": "Placed after 14:23 in the SBLGNT text", "ROM.16.26": "Placed after 14:23 in the SBLGNT text",
     "ROM.16.27": "Placed after 14:23 in the SBLGNT text"},
  "zh-cuv-s": {"JHN.7.53": "Joined to 8:1 in the CUV"}, "zh-cuv-t": {"JHN.7.53": "Joined to 8:1 in the CUV"},
  "hbo-wlc": dict(JOINED),
  "ko-krv": {**{r: "Printed as (eopseum, ‘none’) — not in the text of this edition (check against a printed copy)"
                for r in ["MAT.18.11", "MRK.9.44", "MRK.9.46", "MRK.11.26", "MRK.15.28", "LUK.17.36", "LUK.23.17",
                          "ACT.8.37", "ACT.15.34", "ACT.28.29", "ROM.16.24"]},
             "2CO.13.14": "Numbered 13:13 in this edition"},
  "en-bbe": {"JHN.5.4": "Not in this translation (follows the Revised Version text)",
             "ROM.16.24": "Not in this translation (follows the Revised Version text)"},
  "en-web": {"ROM.16.26": "Placed after 14:23 (as 14:25–26) in this edition",
             "ROM.16.27": "Placed after 14:23 in this edition"},
  **{k: {"001.1": "The basmala is not counted as a verse in this count"}
     for k in ("ar-warsh", "ar-qalun", "ar-duri", "ar-susi")},
}

def additional_reason(key, ref):
    b, *rest = ref.split(".")
    if key == "hbo-wlc":
        return "Psalm title counted as a verse" if b == "PSA" and rest[-1] in ("1", "2") else "The Hebrew divides a KJV verse in two"
    if ref in ("3JN.1.15", "REV.12.18"):
        return "The last verse is divided differently (modern numbering)"
    return "Beyond the KJV numbering"

def iv(v):
    try: return int(v)
    except ValueError: return None

def load_version(d):
    got = defaultdict(dict)   # (book, chapter) -> {verse: row}
    for p in glob.glob(f"{d}/*/*.tsv") + glob.glob(f"{d}/*.tsv"):
        rel = os.path.relpath(p, d)[:-4].split(os.sep)
        book, ch = (rel[0], rel[1]) if len(rel) == 2 else (rel[0], "1")
        with open(p, encoding="utf-8") as f:
            for line in f:
                row = line.rstrip("\n").split("\t")
                if row[0]: got[(book, ch)][row[0]] = row
    return got

def ranges(nums):
    nums = sorted(nums); out = []; s = p = None
    for n in nums:
        if s is None: s = p = n
        elif n == p + 1: p = n
        else: out.append(f"{s}" if s == p else f"{s}-{p}"); s = p = n
    if s is not None: out.append(f"{s}" if s == p else f"{s}-{p}")
    return ",".join(out)

def counts(got, order):
    return {b: [max((iv(v) or 0) for v in got[(b, str(c))]) if (b, str(c)) in got else 0
                for c in range(1, 1 + max((int(c) for (bb, c) in got if bb == b), default=0))] for b in order}

def main(lib):
    vroot = f"{lib}/versions"
    coll = json.load(open(f"{vroot}/collections.json", encoding="utf-8"))
    bible = next(c for c in coll["collections"] if c["id"] == "bible")
    order = [b["code"] for b in bible["books"]]
    names = {b["code"]: b["name"] for b in bible["books"]}
    OT_BOOKS, NT_BOOKS = set(order[:39]), set(order[39:])
    vers = {c: sorted(glob.glob(f"{vroot}/{c}/*/version.json")) for c in ("bible", "quran")}
    data = {p: load_version(os.path.dirname(p)) for c in vers for p in vers[c]}
    keyed = {os.path.basename(os.path.dirname(p)): p for c in vers for p in vers[c]}

    kjv = counts(data[keyed["en-kjv"]], order)
    heb = counts(data[keyed["hbo-wlc"]], order[:39])
    masoretic = kjv_to_masoretic(kjv, heb)
    os.makedirs(f"{lib}/schemes", exist_ok=True)
    json.dump({"id": "kjv", "collection": "bible", "total": sum(map(sum, kjv.values())), "books": kjv},
              open(f"{lib}/schemes/kjv.json", "w"), indent=1)
    json.dump({"id": "masoretic", "collection": "bible", "total": sum(map(sum, heb.values())), "books": heb,
               "fromKJV": masoretic, "joined": JOINED}, open(f"{lib}/schemes/masoretic.json", "w"), indent=1)
    hafs = {b: max(iv(v) for v in vs) for (b, _), vs in data[keyed["ar-hafs"]].items()}
    json.dump({"id": "kufan", "collection": "quran", "total": sum(hafs.values()),
               "books": {b: [hafs[b]] for b in sorted(hafs)}}, open(f"{lib}/schemes/kufan.json", "w"), indent=1)

    report = {"generated": __import__("datetime").date.today().isoformat(),
              "reference": {"bible": sum(map(sum, kjv.values())), "masoretic": sum(map(sum, heb.values())),
                            "quran": sum(hafs.values()), "masoreticShifts": len(masoretic)},
              "versions": []}
    for c in ("bible", "quran"):
        for p in vers[c]:
            meta = json.load(open(p, encoding="utf-8")); got = data[p]; key = meta["key"]
            cov = meta.get("coverage", {})
            reasons = {**cov.get("notes", {}), **SEED.get(key, {})}
            omitted = set(cov.get("omitted", [])) | set(reasons)
            books, missing, extra, kept = {}, [], [], []
            total = sum(len(s) for s in got.values())
            if c == "bible":
                maso = meta.get("numbering") == "masoretic"
                claimed = set()
                have_books = {bb for (bb, _) in got}
                for b in order:
                    if b not in have_books: continue
                    whole = OT_BOOKS <= have_books if b in OT_BOOKS else NT_BOOKS <= have_books
                    chs = sorted(int(ch) for (bb, ch) in got if bb == b)
                    nch = len(kjv[b])
                    if maso: whole = True
                    full = whole or set(range(1, nch + 1)) <= set(chs)
                    books[b] = "all" if full else ranges(chs)
                    for ch in (range(1, nch + 1) if full else chs):
                        for v in range(1, (kjv[b][ch - 1] if ch <= nch else 0) + 1):
                            ref = f"{b}.{ch}.{v}"
                            at = masoretic.get(ref, ref) if maso else ref
                            hb, hc, hv = at.split(".")
                            if hv in got.get((hb, hc), {}): claimed.add(at)
                            elif ref in omitted: kept.append(ref)
                            else: missing.append(ref)
                for (bb, ch), vs in got.items():
                    for v in vs:
                        ref = f"{bb}.{ch}.{v}"
                        if maso:
                            if ref not in claimed: extra.append(ref)
                        elif int(ch) > len(kjv.get(bb, [])) or (iv(v) or 0) > kjv[bb][int(ch) - 1]:
                            extra.append(ref)
            else:
                for (b, _), vs in sorted(got.items()): books[b] = "all"
                if meta["numbering"] == "kufan":
                    for b, n in hafs.items():
                        for v in range(1, n + 1):
                            ref = f"{b}.{v}"
                            if str(v) not in got.get((b, "1"), {}):
                                (kept if ref in omitted else missing).append(ref)
                else:   # own count: every Hafs verse should fall inside some verse's hafsStart..hafsEnd
                    covered = set()
                    for (b, _), vs in got.items():
                        for row in vs.values():
                            if len(row) >= 4:
                                sv, ev = int(row[2].split(":")[1]), int(row[3].split(":")[1])
                                covered.update(f"{b}.{x}" for x in range(sv, ev + 1))
                    for b, n in hafs.items():
                        for v in range(1, n + 1):
                            if f"{b}.{v}" not in covered:
                                (kept if f"{b}.{v}" in omitted else missing).append(f"{b}.{v}")
                    if meta["numbering"] in QURAN_TOTALS and total != QURAN_TOTALS[meta["numbering"]]:
                        missing.append(f"total {total} ≠ {QURAN_TOTALS[meta['numbering']]}")
            extra_notes = {r: additional_reason(key, r) for r in extra}
            meta["coverage"] = {"books": books, "omitted": sorted(omitted), "additional": sorted(extra),
                                **({"notes": reasons} if reasons else {}),
                                **({"additionalNotes": extra_notes} if extra_notes else {})}
            json.dump(meta, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            report["versions"].append({"collection": c, "key": key, "name": meta.get("name"), "short": meta.get("short"),
                "language": meta.get("language"), "license": meta.get("license"), "numbering": meta.get("numbering"),
                "verses": total, "books": len(books),
                "partial": {b: r for b, r in books.items() if r != "all"},
                "missing": missing, "omitted": {r: reasons.get(r, "") for r in sorted(kept)},
                "additional": {r: extra_notes[r] for r in sorted(extra)}, "access": meta.get("access")})

    json.dump(report, open(f"{vroot}/gap-report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lines = ["# Gap report", "", f"Generated {report['generated']}. References: KJV {report['reference']['bible']} verses; "
             f"Masoretic {report['reference']['masoretic']} ({len(masoretic)} KJV verses renumbered); "
             f"Qur'an Kufan {report['reference']['quran']}.", ""]
    for v in report["versions"]:
        lines += [f"## {v['collection']} · {v['key']} — {v['name']}",
                  f"- verses {v['verses']} · numbering {v['numbering']} · books {v['books']}"]
        if v["partial"]: lines.append("- partial: " + "; ".join(f"{b} {r}" for b, r in v["partial"].items()))
        if v["omitted"]: lines.append(f"- omitted/joined in this edition: {len(v['omitted'])}")
        if v["missing"]: lines.append(f"- possibly data errors: {len(v['missing'])}: " + ", ".join(v["missing"][:40])
                                      + (" …" if len(v["missing"]) > 40 else ""))
        if v["additional"]: lines.append(f"- additional: {len(v['additional'])}: " + ", ".join(list(v["additional"])[:20])
                                         + (" …" if len(v["additional"]) > 20 else ""))
        lines.append("")
    open(f"{vroot}/gap-report.md", "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))

if __name__ == "__main__":
    main(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Documents/workspace_chinese/ReaderText"))
