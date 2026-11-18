"""An approximate romanization of vocalized Arabic (the Qur'an's Uthmani text), close to the
usual scholarly style: bismi llāhi r-raḥmāni r-raḥīm. Generated, not a published
transliteration: long vowels, doubling, the article's assimilation (ar-raḥmān), the joining
alif (ٱ) and the pause at a verse's end are handled; finer reading rules (tajwīd) are not."""
import re
import unicodedata

CONSONANTS = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "ḥ", "خ": "kh", "د": "d", "ذ": "dh", "ر": "r",
    "ز": "z", "س": "s", "ش": "sh", "ص": "ṣ", "ض": "ḍ", "ط": "ṭ", "ظ": "ẓ", "ع": "ʿ", "غ": "gh",
    "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y",
    "ء": "ʾ", "أ": "ʾ", "إ": "ʾ", "ؤ": "ʾ", "ئ": "ʾ", "ة": "h", "ی": "y",
}
SUN = set("تثدذرزسشصضطظلن")
FATHA, DAMMA, KASRA = "َ", "ُ", "ِ"
TANWEEN = {"ً": "an", "ٌ": "un", "ٍ": "in"}
SHADDA, SUKUN, QSUKUN, DAGGER, MADDA = "ّ", "ْ", "ۡ", "ٰ", "ٓ"
WASLA, ALIF, ALIF_MAQSURA, MADDA_ALIF = "ٱ", "ا", "ى", "آ"
SMALL_WAW, SMALL_YA = "ۥ", "ۦ"
VOWELS = {FATHA: "a", DAMMA: "u", KASRA: "i"}
# Pause marks, small letters and other Qur'anic signs that aren't read here.
SKIP = set("ـۖۗۘۙۚۛۜ۝۞ۣ۟۠ۢۤ"
           "ۧۨ۩۪ۭ۫۬‏‎ٕٔ")


def word(w, first_in_verse):
    """One word (a list of letters, each with its marks) to Latin."""
    bare = "".join(c for c in w if not unicodedata.combining(c) and c not in SKIP)
    ending = next((VOWELS[m] for m in reversed(w) if m in VOWELS), "")
    if bare in ("ٱلله", "الله"):
        return ("a" if first_in_verse else "") + "llāh" + ending
    if bare == "لله":
        return "lillāh" + ending
    # Split into (letter, marks).
    units = []
    for ch in w:
        if ch in SKIP:
            continue
        if unicodedata.combining(ch) or ch in (SHADDA, SUKUN, QSUKUN, DAGGER, MADDA, SMALL_WAW, SMALL_YA) or ch in TANWEEN or ch in VOWELS:
            if units:
                units[-1][1].append(ch)
            continue
        units.append([ch, []])
    out = []
    prev_vowel = ""
    i = 0
    while i < len(units):
        ch, marks = units[i]
        nxt = units[i + 1] if i + 1 < len(units) else None
        vowel = next((VOWELS[m] for m in marks if m in VOWELS), "")
        tanween = next((TANWEEN[m] for m in marks if m in TANWEEN), "")
        doubled = SHADDA in marks
        dagger = DAGGER in marks
        if ch == WASLA:
            # The joining alif: read only at the start of a verse (a- before the article, i- else).
            if first_in_verse and i == 0:
                out.append("a" if nxt and nxt[0] == "ل" else "i")
            i += 1
            continue
        if ch == MADDA_ALIF:
            out.append("ʾā")
            prev_vowel = "ā"
            i += 1
            continue
        if ch == ALIF_MAQSURA and (vowel or doubled or tanween):
            ch = "ي"
        if ch in (ALIF, ALIF_MAQSURA):
            if prev_vowel == "a":
                out[-1] = out[-1][:-1] + "ā" if out and out[-1].endswith("a") else out[-1]
                prev_vowel = "ā"
            elif tanween:            # the alif after -an
                pass
            elif i == 0:
                out.append(vowel or "a")
                prev_vowel = vowel or "a"
            i += 1
            continue
        if ch == "ل" and i <= 1 and nxt and nxt[0] in SUN and SHADDA in nxt[1] and (i == 1 and units[0][0] in (WASLA, ALIF)):
            # The article before a sun letter: al-raḥmān → ar-raḥmān (the l takes the letter's sound).
            out.append(CONSONANTS[nxt[0]] + "-")
            i += 1
            continue
        if ch == "ل" and i == 1 and units[0][0] in (WASLA, ALIF) and set(marks) <= {SUKUN, QSUKUN}:
            out.append("l-")
            prev_vowel = ""
            i += 1
            continue
        if ch in ("و", "ي") and not vowel and not doubled and not tanween and SUKUN not in marks and QSUKUN not in marks:
            # A long vowel after its short one: -ū, -ī.
            if prev_vowel == "u" and ch == "و":
                out[-1] = out[-1][:-1] + "ū"
                prev_vowel = "ū"
                i += 1
                continue
            if prev_vowel == "i" and ch == "ي":
                out[-1] = out[-1][:-1] + "ī"
                prev_vowel = "ī"
                i += 1
                continue
        if ch == "ة" and not vowel and not tanween:
            out.append("h")
            prev_vowel = ""
            i += 1
            continue
        latin = CONSONANTS.get(ch)
        if latin is None:
            out.append(ch)
            i += 1
            continue
        if ch == "ة":
            latin = "t"
        text = latin * 2 if doubled and out and not out[-1].endswith("-") else latin
        if dagger:
            text += "ā"
            prev_vowel = "ā"
        elif tanween:
            text += tanween
            prev_vowel = ""
        elif vowel:
            text += vowel
            prev_vowel = vowel
        else:
            prev_vowel = ""
        if SMALL_WAW in marks:
            text += "ū" if not text.endswith("u") else ""
        if SMALL_YA in marks:
            text += "ī" if not text.endswith("i") else ""
        out.append(text)
        i += 1
    return "".join(out)


def verse(text):
    words = [w for w in text.split() if any(not unicodedata.combining(c) and c not in SKIP for c in w)]
    latin = [word(w, n == 0) for n, w in enumerate(words)]
    if latin:
        # The pause at a verse's end: no final short vowel or -n (raḥīmi → raḥīm, -an → -ā).
        last = latin[-1]
        if last.endswith("an"):
            last = last[:-2] + "ā"
        elif last.endswith(("un", "in")):
            last = last[:-2]
        elif last.endswith(("a", "u", "i")) and not last.endswith(("ā", "ū", "ī")):
            last = last[:-1]
        latin[-1] = last
    s = " ".join(latin)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1].upper() + s[1:]
