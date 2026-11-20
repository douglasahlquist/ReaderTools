#!/usr/bin/env python3
"""What the app needs to read the version folders, after build_versions.py and gap_analysis.py:

  versions/<c>/<key>/<key>.pack   the version's chapter files in one download (the app's pack format,
                                  read by LibraryPack.swift); version.json's "pack" gives its sha and size
  versions/collections.json       + book names (Chinese, pinyin) and Qur'an page slugs
  versions/bible/paragraphs.json  where each chapter's groups start, as on the passage pages

The pack is also the unit a restricted version will be encrypted as.

  python3 version_packs.py ~/Documents/workspace_chinese/ReaderText
"""
import glob, hashlib, json, os, re, struct, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bible"))


def write_pack(lib, folder, key):
    files = sorted(p for p in glob.glob(f"{folder}/**/*.tsv", recursive=True))
    entries, blobs, offset, digest = [], [], 0, hashlib.sha256()
    for p in files:
        raw = open(p, "rb").read()
        rel = os.path.relpath(p, lib).replace(os.sep, "/")
        digest.update(rel.encode() + b"\0" + raw)
        packer = zlib.compressobj(9, zlib.DEFLATED, -15)
        blob = packer.compress(raw) + packer.flush()
        entries.append({"p": rel, "o": offset, "c": len(blob), "u": len(raw)})
        blobs.append(blob); offset += len(blob)
    sha = digest.hexdigest()[:16]
    index = json.dumps({"built": sha, "files": entries}, separators=(",", ":")).encode()
    path = f"{folder}/{key}.pack"
    with open(path, "wb") as f:
        f.write(b"CRLP" + struct.pack("<I", len(index)) + index)
        for b in blobs: f.write(b)
    return {"file": f"{key}.pack", "sha": sha, "bytes": os.path.getsize(path), "files": len(entries)}


def paragraphs(lib, books):
    """{"JHN.3": [1, 6, 11, …]} from the group headings of the whole-chapter pages."""
    out = {}
    slug2code = {b["slug"]: b["code"] for b in books}
    for p in glob.glob(f"{lib}/bible/passages/*.md"):
        m = re.match(r"(.+)-(\d+)\.(wlc|kjv)\.md$", os.path.basename(p))
        if not m or m[1] not in slug2code: continue
        starts = [int(h) for h in re.findall(r"^## 第(\d+)", open(p, encoding="utf-8").read(), re.M)]
        if starts: out[f"{slug2code[m[1]]}.{int(m[2])}"] = starts
    return dict(sorted(out.items()))


def main(lib):
    import bible_pages as bp
    coll_path = f"{lib}/versions/collections.json"
    coll = json.load(open(coll_path, encoding="utf-8"))
    for c in coll["collections"]:
        if c["id"] == "bible":
            for b, (en, zh, py, *_ ) in zip(c["books"], bp.bs.BOOKS):
                b["zh"], b["pinyin"] = zh, py
        if c["id"] == "quran":
            slugs = {os.path.basename(p)[:3]: os.path.basename(p)[:-3]
                     for p in glob.glob(f"{lib}/islam/quran/[0-9][0-9][0-9]-*.md")}
            for b in c["books"]: b["slug"] = slugs.get(b["code"], b["code"])
    json.dump(coll, open(coll_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    bible = next(c for c in coll["collections"] if c["id"] == "bible")
    json.dump(paragraphs(lib, bible["books"]), open(f"{lib}/versions/bible/paragraphs.json", "w"), separators=(",", ":"))
    for meta_path in sorted(glob.glob(f"{lib}/versions/*/*/version.json")):
        folder = os.path.dirname(meta_path); key = os.path.basename(folder)
        meta = json.load(open(meta_path, encoding="utf-8"))
        meta["pack"] = write_pack(lib, folder, key)
        json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"{key:16} {meta['pack']['files']:5} files  {meta['pack']['bytes'] / 1e6:5.2f} MB  {meta['pack']['sha']}")


if __name__ == "__main__":
    main(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Documents/workspace_chinese/ReaderText"))
