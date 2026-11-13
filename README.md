# ChineseReaderTools

Scripts that build pages for the **Chinese Reader** app. They write into
[ChineseReaderText](https://github.com/douglasahlquist/ChineseReaderText), which they expect to
find beside this folder:

```
workspace_chinese/
├── ChineseReader/          the app
├── ChineseReaderText/      the pages the app reads
└── ChineseReaderTools/     these scripts
```

Set `CHINESEREADER_TEXT=/path/to/ChineseReaderText` (or pass `--text-repo`) if it lives elsewhere.

## Setup

```
cd ChineseReaderTools
python3 -m venv .venv && . .venv/bin/activate      # optional
pip3 install -r requirements.txt
```

## Tools

| Folder | What it builds |
|---|---|
| [`bible/`](bible/README.md) | Bible passages. `bible_fetch.py` downloads books into `sources/`; `bible_pages.py` builds pages (Hanzi with pinyin, then the Greek or Hebrew, the English and other versions, one row each) in one or more editions, and the Passages list |

`sources/` holds the downloaded Bible texts, one file per version per book; check them in.

The HSK course builder is still in `ChineseReaderText/tools/hsk/`.
