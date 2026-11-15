#!/usr/bin/env python3
"""The whole Old Testament for ChineseReaderText: one page per chapter
(bible/passages/<book>-<chapter>.wlc.md) with, under each verse, simplified Hanzi, pinyin and
traditional Hanzi, the Hebrew (Westminster Leningrad Codex, vowel points kept, cantillation marks
left out), the King James Version, and Korean (개역한글), Vietnamese (1934), Thai (ThaiKJV), French
(Martin 1744) and German (Luther 1912). The app shows the versions the user picks
(Settings › Bible Versions).

Nothing is added twice: complete pages are left alone; pages made earlier with fewer rows are
rebuilt in place with all of them; other editions aren't touched. Run it again any time.

    python3 bible/old_testament.py --dry-run                  # what it would build, and stop
    python3 bible/old_testament.py                            # Genesis … Malachi (929 chapters)
    python3 bible/old_testament.py Genesis Psalms             # only these books
    python3 bible/old_testament.py --english none             # no English row
    python3 bible/old_testament.py --languages vietnamese     # only Vietnamese as another language
    python3 bible/old_testament.py --no-languages             # Chinese, Hebrew and English only
    python3 bible/old_testament.py --force                    # rebuild every page
"""
import testament_pages as tp


def main():
    p = tp.parser(__doc__)
    p.add_argument("--english", default="kjv", help="the English version (default kjv; none for no English)")
    tp.add_common_arguments(p)
    args = p.parse_args()
    versions = ["wlc"] + ([] if args.english == "none" else [args.english])
    tp.run(args, testament="Old", book_range=range(1, 40), versions=versions,
           edition="wlc", chapters_from="wlc")


if __name__ == "__main__":
    main()
