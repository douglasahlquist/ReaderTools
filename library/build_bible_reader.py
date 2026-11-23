#!/usr/bin/env python3
"""The English versions for BibleReader, in one step.

1. Public-domain English Bibles from BibleSources (ASV, YLT, Darby, Webster, AKJV; KJV, WEB and BBE
   are already built) go into ReaderText as version folders and packs, like the other versions:
       versions/bible/<key>/<USFM>/<chapter>.tsv, version.json, <key>.pack
   They're also added to bible/versions.json (the app's catalog) and versions/collections.json.
   Each one's source is the downloaded copy when BibleSources has it, else the "-input" import.
2. bundles/BibleReader.json: the same required and default versions as ChineseReader, with every
   English Bible offered for download after the install.
3. NASB and AMP (© The Lockman Foundation) become personal packs in BibleSources/personal, never in
   ReaderText (which is public). They go only into builds for your own devices:
       scripts/deploy.sh all en-nasb en-amp
   and every distribution build refuses a pack that holds them.

Nothing is committed or pushed. The versions are listed in build_versions.py's BIBLE and NAMES, so
a full rerun of build_versions.py keeps them.

  python3 build_bible_reader.py                  # everything
  python3 build_bible_reader.py --list           # what would be built, and from which source
  python3 build_bible_reader.py --only en-ylt    # some versions only
  python3 build_bible_reader.py --no-personal    # skip NASB and AMP
  python3 build_bible_reader.py --no-gaps        # skip the coverage check (gap_analysis.py)
  --library DIR    ReaderText (default ~/Documents/workspace_chinese/ReaderText)
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_versions as bv          # BibleSources (as bv.bs), the books, the version layout
import version_packs as vp

# Public domain: built into ReaderText. (KJV, WEB, BBE are already there.)
PUBLIC = ["en-asv", "en-ylt", "en-darby", "en-webster", "en-akjv"]
ALREADY = ["en-kjv", "en-web", "en-bbe"]
# Copyrighted: personal packs only. BibleSources folder names (with or without "-input").
PERSONAL = {"nasb": "New American Standard Bible (NASB)", "amp": "Amplified Bible (AMP)"}
NEVER_IN_LIBRARY = {"nasb", "amp"}

WORKSPACE = os.path.normpath(os.path.join(HERE, "..", ".."))
APP_SCRIPTS = os.path.join(WORKSPACE, "ChineseReader", "scripts")


def say(text=""):
    print(text, flush=True)


def build_public(lib, keys):
    """Writes each version's chapter files and version.json; returns [(key, verses, source)]."""
    catalog = json.load(open(f"{lib}/bible/versions.json", encoding="utf-8"))
    old = {v["id"]: v for v in catalog["versions"]}
    done = []
    for key in keys:
        src, oid = bv.BIBLE[key]
        source = bv.resolve_source(src)
        if not source:
            say(f"  {key:12} skipped: none of {', '.join(src)} is in BibleSources")
            continue
        if source.replace("-input", "") in NEVER_IN_LIBRARY:
            sys.exit(f"STOP: {key} would come from {source}, which is copyrighted")
        chapters = bv.bible_chapters(lib, key, source, oid, {})
        if not chapters:
            say(f"  {key:12} skipped: {source} has no chapters")
            continue
        folder = f"{lib}/versions/bible/{key}"
        verses = 0
        for (usfm, ch), rows in chapters.items():
            os.makedirs(f"{folder}/{usfm}", exist_ok=True)
            with open(f"{folder}/{usfm}/{ch}.tsv", "w", encoding="utf-8") as f:
                for row in rows:
                    f.write("\t".join(bv.clean(c) for c in row) + "\n")
                    verses += 1
        name, short, lang, lic, numbering = bv.NAMES[key]
        meta = {"key": key, "collection": "bible", "name": name, "short": short,
                "language": lang, "script": bv.SCRIPT.get(lang, ""), "kind": "translation",
                "license": lic, "numbering": numbering, "levels": ["book", "chapter", "verse"],
                "columns": ["verse", "text"], "source": source, "legacyID": oid, "verses": verses,
                "coverage": {"books": {}, "omitted": [], "additional": []}}
        bv.write_json(f"{folder}/version.json", bv.merge_meta(f"{folder}/version.json", meta))
        # The app's catalog: one entry per version id (kept as it is when already there).
        if oid not in old:
            entry = {"id": oid, "short": short, "kind": "translation", "language": lang, "labels": [short],
                     "title": name, "license": lic, "source": "github"}
            catalog["versions"].append(entry)
            old[oid] = entry
        done.append((key, verses, source))
        say(f"  {key:12} {verses:6} verses  from {source}")
    bv.write_json(f"{lib}/bible/versions.json", catalog)

    # collections.json: add the new keys, keep everything else as it is.
    path = f"{lib}/versions/collections.json"
    coll = json.load(open(path, encoding="utf-8"))
    listed = {v["key"] for v in coll["versions"]}
    for key, _, _ in done:
        if key not in listed:
            coll["versions"].append({"collection": "bible", "key": key, "legacyIDs": [bv.BIBLE[key][1]]})
    bv.write_json(path, coll)
    return done


def pack(lib, keys):
    for key in keys:
        folder = f"{lib}/versions/bible/{key}"
        meta_path = f"{folder}/version.json"
        meta = json.load(open(meta_path, encoding="utf-8"))
        meta["pack"] = vp.write_pack(lib, folder, key)
        bv.write_json(meta_path, meta)
        say(f"  {key:12} {meta['pack']['files']:5} files  {meta['pack']['bytes'] / 1e6:5.2f} MB")


def write_bundle(lib):
    """bundles/BibleReader.json: ChineseReader's required and default versions, all English offered."""
    chinese = json.load(open(f"{lib}/bundles/ChineseReader.json", encoding="utf-8"))
    present = {os.path.basename(os.path.dirname(p)) for p in
               __import__("glob").glob(f"{lib}/versions/bible/*/version.json")}
    english = [k for k in ALREADY + PUBLIC if k in present and k not in chinese["default"]]
    bundle = {
        "app": "BibleReader",
        "_about": chinese.get("_about", ""),
        "required": chinese["required"],
        "default": chinese["default"],
        "offered": english,
        "hidden": [],
    }
    bv.write_json(f"{lib}/bundles/BibleReader.json", bundle)
    say(f"  bundles/BibleReader.json: default {', '.join(bundle['default'])}")
    say(f"                            offered {', '.join(english) or '(none)'}")


def build_personal(lib):
    """NASB and AMP as personal packs, through content_pack.py's converter (bible_personal.py)."""
    sys.path.insert(0, APP_SCRIPTS)
    import content_pack as cp
    available = cp.source_versions(lib)
    keys = []
    for base, title in PERSONAL.items():
        match = [(k, i) for k, i in available.items()
                 if os.path.basename(os.path.dirname(i["dir"])).replace("-input", "") == base]
        if not match:
            say(f"  {base}: not found in BibleSources (or already built); skipped")
            continue
        key, info = match[0]
        info = dict(info, name=title, license="Copyrighted (The Lockman Foundation): private use only")
        cp.convert_source(key, info, [cp.PERSONAL_DEFAULT])
        keys.append(key)
    if keys:
        say(f"  personal packs in {cp.PERSONAL_DEFAULT}")
        say(f"  for your own devices: scripts/deploy.sh all {' '.join(keys)}")
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default=os.path.expanduser("~/Documents/workspace_chinese/ReaderText"))
    ap.add_argument("--only", nargs="+", metavar="KEY", help="some of: " + ", ".join(PUBLIC))
    ap.add_argument("--list", action="store_true", help="show what would be built and from where")
    ap.add_argument("--no-personal", action="store_true", help="skip NASB and AMP")
    ap.add_argument("--no-gaps", action="store_true", help="skip gap_analysis.py")
    args = ap.parse_args()
    lib = os.path.expanduser(args.library)
    keys = args.only or PUBLIC
    unknown = [k for k in keys if k not in PUBLIC]
    if unknown:
        sys.exit(f"Not a public English version here: {', '.join(unknown)} (known: {', '.join(PUBLIC)})")

    if args.list:
        say("Public domain, into ReaderText:")
        for key in keys:
            src, _ = bv.BIBLE[key]
            say(f"  {key:12} {bv.resolve_source(src) or '(not in BibleSources: ' + ', '.join(src) + ')'}")
        say("Personal only (BibleSources/personal): " + ", ".join(PERSONAL))
        return

    say("1. Public-domain English versions")
    done = build_public(lib, keys)
    built = [k for k, _, _ in done]
    if built and not args.no_gaps:
        say("2. Coverage (gap_analysis.py)")
        result = subprocess.run([sys.executable, os.path.join(HERE, "gap_analysis.py"), lib],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            say("  done: versions/gap-report.md")
        else:
            last = (result.stderr.strip().splitlines() or ["?"])[-1]
            say(f"  WARNING: gap_analysis.py failed ({last}); coverage not updated, packs built anyway")
    if built:
        say("3. Packs")
        pack(lib, built)
    say("4. BibleReader's bundle")
    write_bundle(lib)
    if not args.no_personal:
        say("5. NASB and AMP (personal)")
        build_personal(lib)
    say()
    say("Nothing committed. ReaderText now has new public-domain files to review and push:")
    say(f"  cd {lib} && git status --short versions bible bundles")


if __name__ == "__main__":
    main()
