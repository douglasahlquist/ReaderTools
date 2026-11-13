# Bible passages

Two steps: **fetch** the texts into `sources/` (once per book and version), then **build** pages
from them into ChineseReaderText. Both run from the ChineseReaderTools folder.

```
. .venv/bin/activate                                  # see the top-level README for setup

python3 bible/bible_fetch.py Romans Psalms            # download the books every edition needs
python3 bible/bible_pages.py "Romans 12" "Psalm 23"   # build the default edition
python3 bible/bible_pages.py "Romans 12" --all-editions
git -C ../ChineseReaderText status bible/             # the new pages and the updated list
```

## 1. Fetch: `bible_fetch.py`

Downloads books into `sources/<version>/<NN-book>.json`: one file per version per book, one
verse per line, so git diffs stay readable. Check `sources/` in: page builds are then
repeatable and work offline.

```
python3 bible/bible_fetch.py Romans                     # the versions editions.json uses
python3 bible/bible_fetch.py Romans --versions kjv,tr   # just these
python3 bible/bible_fetch.py --nt --versions sblgnt     # the whole New Testament
python3 bible/bible_fetch.py --all                      # everything the editions use (~70 MB)
python3 bible/bible_fetch.py --list                     # what's in sources/
python3 bible/bible_fetch.py Romans --refresh           # download again
```

Books are named in English or Chinese (`Romans`, `1 Corinthians`, `罗马书`). A version that
doesn't cover a book (Greek in the Old Testament, Hebrew in the New, JPS in the New) is skipped.
The large upstream files are kept in `~/.cache/chinesereader-bible`, not in the repo.

`sources/cuv/` is the Chinese Union Version as published (traditional, with its spacing); the
builder makes the simplified text from it.

## 2. Build: `bible_pages.py`

```
python3 bible/bible_pages.py "Romans 12"                 # one chapter
python3 bible/bible_pages.py Romans                      # every chapter: romans-1.md … romans-16.md
python3 bible/bible_pages.py "Romans 12-14"              # a run of chapters
python3 bible/bible_pages.py "John 3:16" "Romans 8:28-39"   # verses
python3 bible/bible_pages.py "罗马书 12"                  # Chinese book names work too
python3 bible/bible_pages.py --index-only                # just rebuild the Passages list
python3 bible/bible_pages.py --editions                  # editions and versions
```

If a source is missing, nothing is written and the script prints the `bible_fetch.py` command
that gets it.

### Editions

An **edition** is a named set of versions, defined in [`editions.json`](editions.json):

| Edition | Chinese | Greek / Hebrew | English |
|---|---|---|---|
| `study` (default) | 和合本 simplified + traditional | SBLGNT / WLC | WEB |
| `classic` | 和合本 simplified | Textus Receptus / WLC | KJV |
| `basic` | 和合本 simplified | none | Bible in Basic English |

```
python3 bible/bible_pages.py "Romans 12" --edition classic
python3 bible/bible_pages.py "Romans 12" --edition study,classic
python3 bible/bible_pages.py "Romans 12" --all-editions
python3 bible/bible_pages.py "Romans 12" --en web,kjv --as compare     # a one-off edition
```

Add or change editions in `editions.json`; its order is the order of the app's menu, and
`default` names the edition whose pages have the plain file name.

### Files and the list

| Page | File |
|---|---|
| Romans 12, default edition | `bible/passages/romans-12.md` |
| Romans 12, Classic | `bible/passages/romans-12.classic.md` |
| John 3:16 | `bible/passages/john-3-16.md` |
| Romans 8:28–39 | `bible/passages/romans-8-28-39.md` |

(No `:` in file names: the Mac Finder shows it as `/`, Windows can't check such a file out, and
URLs must escape it.)

Each build rebuilds the **经文 Passages** part of ChineseReaderText's `bible/README.md` from the
files in `bible/passages/`. One line per passage, books in Bible order:

```
### 经文 Passages
#### 新约 New Testament
##### 罗马书 Romans
- [12](passages/romans-12.md) · [Study](passages/romans-12.md) · [Classic](passages/romans-12.classic.md)
```

The app lists **Romans › 12** once; a menu on the page switches between Study and Classic (and
remembers the choice for the next passage). A passage with one edition is just the first link.
Settings › *Bible passages in the list* shows the list nested (Passages › New Testament ›
Romans › 12) or as *Book and chapter* (Passages › 罗马书 Romans 12). Everything else in
`bible/README.md` is left as it is.

### The page

Each verse is one row of a table marked `<!-- reader: table=verses -->`:
`| Hanzi | Pinyin | 繁體 | SBLGNT | WEB |`. The app shows the Hanzi (pinyin on tap, words spoken
whole), the traditional under it in its own color, then the Greek or Hebrew (Hebrew right to
left), then the English, then other versions, one row each, unlabeled; the first line of the
page names the edition and its versions. Groups follow the English version's paragraphs (WEB),
else 5 verses (`--group N`).

### Your own text

`--hanzi-file` and `--english-file` take one verse per line (`16 text` or `3:16 text`) and
replace those verses, so a translation that can't be downloaded can still be used. Pinyin always
comes from the Hanzi.

### Pinyin

pypinyin with jieba word splitting, a list of Bible readings (耶和华 Yē hé huá, 弟兄 dì xiong,
得着 dé zháo, 时候 shí hou …) and the tone changes of 不 and 一. Check each page: a word with two
readings can still come out wrong. Fixes go in `PHRASES`, `SINGLE`, `DE_GET`, `WEI_AFTER` and the
word lists near the top of `bible_pages.py`.

## Versions

| Key | Version | Covers |
|---|---|---|
| `cuv` | 和合本 Chinese Union Version (1919) | all |
| `web` | World English Bible | all |
| `nheb` | New Heart English Bible | all |
| `kjv` / `akjv` | King James Version (1769) / American KJV | all |
| `asv` | American Standard Version (1901) | all |
| `bbe` | Bible in Basic English (1949/1964) | all |
| `ylt`, `rotherham` | Young's Literal (1898), Rotherham's Emphasized (1902) | all |
| `darby`, `webster`, `noyes`, `tyndale` | Darby (1889), Webster (1833), Noyes (1869), Tyndale (1525/30) | all |
| `jps` | Jewish Publication Society (1917) | Old Testament |
| `sblgnt` | SBL Greek New Testament | New Testament |
| `tr`, `byz` | Textus Receptus (1550/1894), Byzantine Textform (2013) | New Testament |
| `wlc` | Westminster Leningrad Codex (Hebrew; cantillation marks removed on the page) | Old Testament |

All public domain, except the SBLGNT, which is free to use with the attribution its pages carry.
Upstream: scrollmapper/bible_databases, TehShrike/world-english-bible (WEB), morphgnt/sblgnt.
