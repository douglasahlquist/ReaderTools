#!/usr/bin/env python3
"""The whole New Testament for ChineseReaderText: one page per chapter
(bible/passages/<book>-<chapter>.kjv.md) with, under each verse, simplified Hanzi, pinyin and
traditional Hanzi, the Greek, the King James Version, and Korean (개역한글), Vietnamese (1934), Thai
(ThaiKJV), French (Martin 1744) and German (Luther 1912). The app shows the versions the user picks
(Settings › Bible Versions).

Nothing is added twice: complete pages are left alone; pages made earlier with fewer rows are
rebuilt in place with all of them; other editions aren't touched. Run it again any time.

    python3 bible/new_testament.py --dry-run                  # what it would build, and stop
    python3 bible/new_testament.py                            # Matthew … Revelation (260 chapters)
    python3 bible/new_testament.py Matthew Acts               # only these books
    python3 bible/new_testament.py --languages krv,martin     # only Korean and French as other languages
    python3 bible/new_testament.py --no-languages             # Chinese, Greek and KJV only
    python3 bible/new_testament.py --greek tr                 # Textus Receptus instead of SBLGNT
    python3 bible/new_testament.py --force                    # rebuild every page

Greek: SBLGNT by default (accents and breathings, so the app's transliteration reads ὁ as “ho”;
CC BY 4.0, credited on each page). Thai: CC BY-NC-ND 4.0, credited on each page.
"""
import testament_pages as tp


def main():
    p = tp.parser(__doc__)
    p.add_argument("--greek", default="sblgnt", choices=["sblgnt", "tr", "byz"], help="the Greek text (default sblgnt)")
    tp.add_common_arguments(p)
    args = p.parse_args()
    tp.run(args, testament="New", book_range=range(40, 67), versions=[args.greek, "kjv"],
           edition="kjv", chapters_from="kjv")


if __name__ == "__main__":
    main()
