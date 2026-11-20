"""Masoretic (Hebrew Bible) ↔ KJV versification.

SHIFTS: runs of KJV verses that sit at a different Hebrew chapter/verse:
  (book, kjv_chapter, kjv_first, kjv_last, hebrew_chapter, hebrew_first)
Psalms are worked out from the verse counts: where the Hebrew counts the title as verse 1
(or 1-2), every KJV verse is one (or two) higher in the Hebrew.
"""
SHIFTS = [
    ("GEN", 31, 55, 55, 32, 1), ("GEN", 32, 1, 32, 32, 2),
    ("EXO", 8, 1, 4, 7, 26), ("EXO", 8, 5, 32, 8, 1),
    ("EXO", 22, 1, 1, 21, 37), ("EXO", 22, 2, 31, 22, 1),
    ("LEV", 6, 1, 7, 5, 20), ("LEV", 6, 8, 30, 6, 1),
    ("NUM", 16, 36, 50, 17, 1), ("NUM", 17, 1, 13, 17, 16),
    ("NUM", 29, 40, 40, 30, 1), ("NUM", 30, 1, 16, 30, 2),
    ("DEU", 12, 32, 32, 13, 1), ("DEU", 13, 1, 18, 13, 2),
    ("DEU", 22, 30, 30, 23, 1), ("DEU", 23, 1, 25, 23, 2),
    ("DEU", 29, 1, 1, 28, 69), ("DEU", 29, 2, 29, 29, 1),
    ("1SA", 21, 1, 15, 21, 2),
    ("1SA", 23, 29, 29, 24, 1), ("1SA", 24, 1, 22, 24, 2),
    ("2SA", 18, 33, 33, 19, 1), ("2SA", 19, 1, 43, 19, 2),
    ("1KI", 4, 21, 34, 5, 1), ("1KI", 5, 1, 18, 5, 15),
    ("1KI", 22, 44, 53, 22, 45),
    ("2KI", 11, 21, 21, 12, 1), ("2KI", 12, 1, 21, 12, 2),
    ("1CH", 6, 1, 15, 5, 27), ("1CH", 6, 16, 81, 6, 1),
    ("1CH", 12, 5, 40, 12, 6),
    ("2CH", 2, 1, 1, 1, 18), ("2CH", 2, 2, 18, 2, 1),
    ("2CH", 14, 1, 1, 13, 23), ("2CH", 14, 2, 15, 14, 1),
    ("NEH", 4, 1, 6, 3, 33), ("NEH", 4, 7, 23, 4, 1),
    ("NEH", 7, 69, 73, 7, 68),
    ("NEH", 9, 38, 38, 10, 1), ("NEH", 10, 1, 39, 10, 2),
    ("JOB", 41, 1, 8, 40, 25), ("JOB", 41, 9, 34, 41, 1),
    ("ECC", 5, 1, 1, 4, 17), ("ECC", 5, 2, 20, 5, 1),
    ("SNG", 6, 13, 13, 7, 1), ("SNG", 7, 1, 13, 7, 2),
    ("ISA", 9, 1, 1, 8, 23), ("ISA", 9, 2, 21, 9, 1),
    ("ISA", 64, 1, 1, 63, 19), ("ISA", 64, 2, 12, 64, 1),
    ("JER", 9, 1, 1, 8, 23), ("JER", 9, 2, 26, 9, 1),
    ("EZK", 20, 45, 49, 21, 1), ("EZK", 21, 1, 32, 21, 6),
    ("DAN", 4, 1, 3, 3, 31), ("DAN", 4, 4, 37, 4, 1),
    ("DAN", 5, 31, 31, 6, 1), ("DAN", 6, 1, 28, 6, 2),
    ("HOS", 1, 10, 11, 2, 1), ("HOS", 2, 1, 23, 2, 3),
    ("HOS", 11, 12, 12, 12, 1), ("HOS", 12, 1, 14, 12, 2),
    ("HOS", 13, 16, 16, 14, 1), ("HOS", 14, 1, 9, 14, 2),
    ("JOL", 2, 28, 32, 3, 1), ("JOL", 3, 1, 21, 4, 1),
    ("JON", 1, 17, 17, 2, 1), ("JON", 2, 1, 10, 2, 2),
    ("MIC", 5, 1, 1, 4, 14), ("MIC", 5, 2, 15, 5, 1),
    ("NAM", 1, 15, 15, 2, 1), ("NAM", 2, 1, 13, 2, 2),
    ("ZEC", 1, 18, 21, 2, 1), ("ZEC", 2, 1, 13, 2, 5),
    ("MAL", 4, 1, 6, 3, 19),
]
# KJV verses the Hebrew joins to the verse before (no Hebrew verse of their own)
JOINED = {"NEH.7.68": "Not in the Masoretic text (KJV follows Ezra 2:66)"}


def kjv_to_masoretic(kjv_counts, heb_counts):
    """{'GEN.31.55': 'GEN.32.1', …} for every KJV verse whose Hebrew reference differs.
    kjv_counts / heb_counts: {book: [verses in chapter 1, chapter 2, …]}"""
    out = {}
    for b, kc, k1, k2, hc, h1 in SHIFTS:
        for i, v in enumerate(range(k1, k2 + 1)):
            out[f"{b}.{kc}.{v}"] = f"{b}.{hc}.{h1 + i}"
    for ch, (k, h) in enumerate(zip(kjv_counts.get("PSA", []), heb_counts.get("PSA", [])), 1):
        if h - k in (1, 2):
            for v in range(1, k + 1):
                out[f"PSA.{ch}.{v}"] = f"PSA.{ch}.{v + h - k}"
    return out
