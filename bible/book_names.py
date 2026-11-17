#!/usr/bin/env python3
"""Books of the Bible in each language: an Old and a New Testament page per language with every
book's name, a romanization where the script needs one (Korean, Thai), and the name in the
comparison language (English for now: the app's default language). Writes
ChineseReaderText/bible/books/<code>-ot.md and -nt.md, and the 书卷 Books of the Bible section of
bible/README.md: one #### heading per language (English first, compared with Chinese; then Chinese,
with its existing pages; then the others).

    python3 bible/book_names.py                  # every language
    python3 bible/book_names.py --languages ko,fr
    python3 bible/book_names.py --compare en     # the comparison language (only en so far)

Names are the traditional ones of each language's Bible used in the library: 개역한글 (Korean),
Bản Truyền Thống 1925/1934 (Vietnamese), Thai KJV / 1971 (Thai), Louis Segond / Martin (French),
Luther (German). Korean romanization: Revised Romanization; Thai: RTGS, by hand (both stored in this script).
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bible_pages as bp  # noqa: E402

bs = bp.bs

# Book groups: (first book, last book) and their English names.
OT_GROUPS = [((1, 5), "The Law"), ((6, 17), "History"), ((18, 22), "Poetry and Wisdom"),
             ((23, 27), "Major Prophets"), ((28, 39), "Minor Prophets")]
NT_GROUPS = [((40, 43), "The Gospels"), ((44, 44), "History"), ((45, 57), "Letters of Paul"),
             ((58, 65), "General Letters"), ((66, 66), "Prophecy")]

LANGUAGES = {
    "ko": dict(
        name="한국어 Korean", voice="ko-KR", romanize="korean",
        ot="구약 성경", nt="신약 성경",
        ot_groups=["율법서", "역사서", "시가서", "대선지서", "소선지서"],
        nt_groups=["복음서", "역사서", "바울 서신", "공동 서신", "예언서"],
        books="""창세기 출애굽기 레위기 민수기 신명기 여호수아 사사기 룻기 사무엘상 사무엘하 열왕기상 열왕기하
        역대상 역대하 에스라 느헤미야 에스더 욥기 시편 잠언 전도서 아가 이사야 예레미야 예레미야애가 에스겔 다니엘
        호세아 요엘 아모스 오바댜 요나 미가 나훔 하박국 스바냐 학개 스가랴 말라기
        마태복음 마가복음 누가복음 요한복음 사도행전 로마서 고린도전서 고린도후서 갈라디아서 에베소서 빌립보서 골로새서
        데살로니가전서 데살로니가후서 디모데전서 디모데후서 디도서 빌레몬서 히브리서 야고보서 베드로전서 베드로후서
        요한일서 요한이서 요한삼서 유다서 요한계시록""".split()),
    "vi": dict(
        name="Tiếng Việt Vietnamese", voice="vi-VN", romanize=None,
        ot="Cựu Ước", nt="Tân Ước",
        ot_groups=["Ngũ Kinh", "Sách Lịch Sử", "Sách Thơ Ca", "Đại Tiên Tri", "Tiểu Tiên Tri"],
        nt_groups=["Phúc Âm", "Lịch Sử", "Thư Tín Phao-lô", "Thư Tín Chung", "Tiên Tri"],
        books=["Sáng Thế Ký", "Xuất Ê-díp-tô Ký", "Lê-vi Ký", "Dân Số Ký", "Phục Truyền Luật Lệ Ký", "Giô-suê",
               "Các Quan Xét", "Ru-tơ", "I Sa-mu-ên", "II Sa-mu-ên", "I Các Vua", "II Các Vua", "I Sử Ký",
               "II Sử Ký", "E-xơ-ra", "Nê-hê-mi", "Ê-xơ-tê", "Gióp", "Thi Thiên", "Châm Ngôn", "Truyền Đạo",
               "Nhã Ca", "Ê-sai", "Giê-rê-mi", "Ca Thương", "Ê-xê-chi-ên", "Đa-ni-ên", "Ô-sê", "Giô-ên", "A-mốt",
               "Áp-đia", "Giô-na", "Mi-chê", "Na-hum", "Ha-ba-cúc", "Sô-phô-ni", "A-ghê", "Xa-cha-ri", "Ma-la-chi",
               "Ma-thi-ơ", "Mác", "Lu-ca", "Giăng", "Công Vụ Các Sứ Đồ", "Rô-ma", "I Cô-rinh-tô", "II Cô-rinh-tô",
               "Ga-la-ti", "Ê-phê-sô", "Phi-líp", "Cô-lô-se", "I Tê-sa-lô-ni-ca", "II Tê-sa-lô-ni-ca",
               "I Ti-mô-thê", "II Ti-mô-thê", "Tít", "Phi-lê-môn", "Hê-bơ-rơ", "Gia-cơ", "I Phi-e-rơ",
               "II Phi-e-rơ", "I Giăng", "II Giăng", "III Giăng", "Giu-đe", "Khải Huyền"]),
    "th": dict(
        name="ภาษาไทย Thai", voice="th-TH", romanize="thai",
        ot="พันธสัญญาเดิม", nt="พันธสัญญาใหม่",
        ot_groups=["ธรรมบัญญัติ", "ประวัติศาสตร์", "กวีนิพนธ์", "ผู้เผยพระวจนะใหญ่", "ผู้เผยพระวจนะน้อย"],
        nt_groups=["พระกิตติคุณ", "ประวัติศาสตร์", "จดหมายของเปาโล", "จดหมายทั่วไป", "คำพยากรณ์"],
        books=["ปฐมกาล", "อพยพ", "เลวีนิติ", "กันดารวิถี", "เฉลยธรรมบัญญัติ", "โยชูวา", "ผู้วินิจฉัย", "นางรูธ",
               "1 ซามูเอล", "2 ซามูเอล", "1 พงศ์กษัตริย์", "2 พงศ์กษัตริย์", "1 พงศาวดาร", "2 พงศาวดาร", "เอสรา",
               "เนหะมีย์", "เอสเธอร์", "โยบ", "สดุดี", "สุภาษิต", "ปัญญาจารย์", "เพลงซาโลมอน", "อิสยาห์", "เยเรมีย์",
               "เพลงคร่ำครวญ", "เอเสเคียล", "ดาเนียล", "โฮเชยา", "โยเอล", "อาโมส", "โอบาดีห์", "โยนาห์", "มีคาห์",
               "นาฮูม", "ฮาบากุก", "เศฟันยาห์", "ฮักกัย", "เศคาริยาห์", "มาลาคี",
               "มัทธิว", "มาระโก", "ลูกา", "ยอห์น", "กิจการ", "โรม", "1 โครินธ์", "2 โครินธ์", "กาลาเทีย", "เอเฟซัส",
               "ฟีลิปปี", "โคโลสี", "1 เธสะโลนิกา", "2 เธสะโลนิกา", "1 ทิโมธี", "2 ทิโมธี", "ทิตัส", "ฟีเลโมน",
               "ฮีบรู", "ยากอบ", "1 เปโตร", "2 เปโตร", "1 ยอห์น", "2 ยอห์น", "3 ยอห์น", "ยูดา", "วิวรณ์"]),
    "fr": dict(
        name="Français French", voice="fr-FR", romanize=None,
        ot="Ancien Testament", nt="Nouveau Testament",
        ot_groups=["Le Pentateuque", "Livres historiques", "Livres poétiques", "Grands prophètes", "Petits prophètes"],
        nt_groups=["Les Évangiles", "Histoire", "Épîtres de Paul", "Épîtres générales", "Prophétie"],
        books=["Genèse", "Exode", "Lévitique", "Nombres", "Deutéronome", "Josué", "Juges", "Ruth", "1 Samuel",
               "2 Samuel", "1 Rois", "2 Rois", "1 Chroniques", "2 Chroniques", "Esdras", "Néhémie", "Esther", "Job",
               "Psaumes", "Proverbes", "Ecclésiaste", "Cantique des Cantiques", "Ésaïe", "Jérémie", "Lamentations",
               "Ézéchiel", "Daniel", "Osée", "Joël", "Amos", "Abdias", "Jonas", "Michée", "Nahum", "Habacuc",
               "Sophonie", "Aggée", "Zacharie", "Malachie",
               "Matthieu", "Marc", "Luc", "Jean", "Actes", "Romains", "1 Corinthiens", "2 Corinthiens", "Galates",
               "Éphésiens", "Philippiens", "Colossiens", "1 Thessaloniciens", "2 Thessaloniciens", "1 Timothée",
               "2 Timothée", "Tite", "Philémon", "Hébreux", "Jacques", "1 Pierre", "2 Pierre", "1 Jean", "2 Jean",
               "3 Jean", "Jude", "Apocalypse"]),
    "de": dict(
        name="Deutsch German", voice="de-DE", romanize=None,
        ot="Altes Testament", nt="Neues Testament",
        ot_groups=["Gesetz", "Geschichtsbücher", "Poetische Bücher", "Große Propheten", "Kleine Propheten"],
        nt_groups=["Evangelien", "Geschichte", "Briefe des Paulus", "Allgemeine Briefe", "Prophetie"],
        books=["1. Mose", "2. Mose", "3. Mose", "4. Mose", "5. Mose", "Josua", "Richter", "Rut", "1. Samuel",
               "2. Samuel", "1. Könige", "2. Könige", "1. Chronik", "2. Chronik", "Esra", "Nehemia", "Ester", "Hiob",
               "Psalmen", "Sprüche", "Prediger", "Hohelied", "Jesaja", "Jeremia", "Klagelieder", "Hesekiel",
               "Daniel", "Hosea", "Joel", "Amos", "Obadja", "Jona", "Micha", "Nahum", "Habakuk", "Zefanja",
               "Haggai", "Sacharja", "Maleachi",
               "Matthäus", "Markus", "Lukas", "Johannes", "Apostelgeschichte", "Römer", "1. Korinther",
               "2. Korinther", "Galater", "Epheser", "Philipper", "Kolosser", "1. Thessalonicher",
               "2. Thessalonicher", "1. Timotheus", "2. Timotheus", "Titus", "Philemon", "Hebräer", "Jakobus",
               "1. Petrus", "2. Petrus", "1. Johannes", "2. Johannes", "3. Johannes", "Judas", "Offenbarung"]),
}
ORDER = ["en", "ko", "vi", "th", "fr", "de"]

# Korean in Revised Romanization, one entry per word (made once with korean-romanizer, so the
# script needs no extra package).
KOREAN_RR = {
    "갈라디아서": "Galradiaseo", "고린도전서": "Gorindojeonseo", "고린도후서": "Gorindohuseo", "골로새서": "Golrosaeseo",
    "공동": "Gongdong", "구약": "Guyak", "나훔": "Nahum", "누가복음": "Nugabogeum", "느헤미야": "Neuhemiya",
    "다니엘": "Daniel", "대선지서": "Daeseonjiseo", "데살로니가전서": "Desalronigajeonseo", "데살로니가후서": "Desalronigahuseo",
    "디도서": "Didoseo", "디모데전서": "Dimodejeonseo", "디모데후서": "Dimodehuseo", "레위기": "Rewigi", "로마서": "Romaseo",
    "룻기": "Rutgi", "마가복음": "Magabogeum", "마태복음": "Mataebogeum", "말라기": "Malragi", "미가": "Miga",
    "민수기": "Minsugi", "바울": "Baul", "베드로전서": "Bedeurojeonseo", "베드로후서": "Bedeurohuseo", "복음서": "Bogeumseo",
    "빌레몬서": "Bilremonseo", "빌립보서": "Bilripboseo", "사도행전": "Sadohaengjeon", "사무엘상": "Samuelsang",
    "사무엘하": "Samuelha", "사사기": "Sasagi", "서신": "Seosin", "성경": "Seonggyeong", "소선지서": "Soseonjiseo",
    "스가랴": "Seugarya", "스바냐": "Seubanya", "시가서": "Sigaseo", "시편": "Sipyeon", "신명기": "Sinmyeonggi",
    "신약": "Sinyak", "아가": "Aga", "아모스": "Amoseu", "야고보서": "Yagoboseo", "에베소서": "Ebesoseo", "에스겔": "Eseugel",
    "에스더": "Eseudeo", "에스라": "Eseura", "여호수아": "Yeohosua", "역대상": "Yeokdaesang", "역대하": "Yeokdaeha",
    "역사서": "Yeoksaseo", "열왕기상": "Yeorwanggisang", "열왕기하": "Yeorwanggiha", "예레미야": "Yeremiya",
    "예레미야애가": "Yeremiyaaega", "예언서": "Yeeonseo", "오바댜": "Obadya", "요나": "Yona", "요엘": "Yoel",
    "요한계시록": "Yohangyesirok", "요한복음": "Yohanbogeum", "요한삼서": "Yohansamseo", "요한이서": "Yohaniseo",
    "요한일서": "Yohanilseo", "욥기": "Yopgi", "유다서": "Yudaseo", "율법서": "Yulbeopseo", "이사야": "Isaya",
    "잠언": "Jameon", "전도서": "Jeondoseo", "창세기": "Changsegi", "출애굽기": "Churaegupgi", "하박국": "Habakguk",
    "학개": "Hakgae", "호세아": "Hosea", "히브리서": "Hibeuriseo",
}

# Thai in RTGS (the Royal Thai General System), written by hand: automatic romanization of Thai
# names is unreliable. Book numbers ("1 ซามูเอล") are kept in front.
THAI_RTGS = {
    "ปฐมกาล": "Pathommakan", "อพยพ": "Opphayop", "เลวีนิติ": "Lewiniti", "กันดารวิถี": "Kandanwithi",
    "เฉลยธรรมบัญญัติ": "Chaloei Thammabanyat", "โยชูวา": "Yochuwa", "ผู้วินิจฉัย": "Phu Winitchai",
    "นางรูธ": "Nang Rut", "ซามูเอล": "Samuen", "พงศ์กษัตริย์": "Phong Kasat", "พงศาวดาร": "Phongsawadan",
    "เอสรา": "Esara", "เนหะมีย์": "Nehami", "เอสเธอร์": "Esthoe", "โยบ": "Yop", "สดุดี": "Saduti",
    "สุภาษิต": "Suphasit", "ปัญญาจารย์": "Panyachan", "เพลงซาโลมอน": "Phleng Salomon", "อิสยาห์": "Itsaya",
    "เยเรมีย์": "Yeremi", "เพลงคร่ำครวญ": "Phleng Khramkhruan", "เอเสเคียล": "Esekhian", "ดาเนียล": "Danian",
    "โฮเชยา": "Hoseya", "โยเอล": "Yoen", "อาโมส": "Amot", "โอบาดีห์": "Obadi", "โยนาห์": "Yona",
    "มีคาห์": "Mikha", "นาฮูม": "Nahum", "ฮาบากุก": "Habakuk", "เศฟันยาห์": "Sefanya", "ฮักกัย": "Hakkai",
    "เศคาริยาห์": "Sekhariya", "มาลาคี": "Malakhi",
    "มัทธิว": "Matthio", "มาระโก": "Marako", "ลูกา": "Luka", "ยอห์น": "Yon", "กิจการ": "Kitchakan", "โรม": "Rom",
    "โครินธ์": "Khorin", "กาลาเทีย": "Kalathia", "เอเฟซัส": "Efesat", "ฟีลิปปี": "Filippi", "โคโลสี": "Kholosi",
    "เธสะโลนิกา": "Thesalonika", "ทิโมธี": "Thimothi", "ทิตัส": "Thitat", "ฟีเลโมน": "Filemon", "ฮีบรู": "Hibru",
    "ยากอบ": "Yakop", "เปโตร": "Petro", "ยูดา": "Yuda", "วิวรณ์": "Wiwon",
    "พันธสัญญาเดิม": "Phanthasanya Doem", "พันธสัญญาใหม่": "Phanthasanya Mai",
    "ธรรมบัญญัติ": "Thammabanyat", "ประวัติศาสตร์": "Prawattisat", "กวีนิพนธ์": "Kawiniphon",
    "ผู้เผยพระวจนะใหญ่": "Phu Phoei Phra Wachana Yai", "ผู้เผยพระวจนะน้อย": "Phu Phoei Phra Wachana Noi",
    "พระกิตติคุณ": "Phra Kittikhun", "จดหมายของเปาโล": "Chotmai Khong Paolo", "จดหมายทั่วไป": "Chotmai Thuapai",
    "คำพยากรณ์": "Kham Phayakon",
}
COMPARE = {"en": dict(name="English", ot="Books of the Old Testament", nt="Books of the New Testament",
                      book=lambda n: bs.BOOKS[n - 1][0])}


def romanizer(kind):
    if kind == "korean":
        return lambda text: " ".join(w if w.isdigit() else KOREAN_RR[w] for w in text.split())
    if kind == "thai":
        return lambda text: " ".join(w if w.isdigit() else THAI_RTGS[w] for w in text.split())
    return lambda text: ""


def _cap(s):
    return s[:1].upper() + s[1:]


def aligned(native, roman):
    """For titles and headings (shown word by word): one romanized word per native word, so a
    one-word Thai heading gets “Phanthasanya-Mai”."""
    words = native.split()
    parts = roman.split()
    if not roman or len(parts) == len(words):
        return roman
    if len(words) == 1:
        return "-".join(parts)
    return roman


def page(code, info, testament, compare):
    roman = romanizer(info["romanize"])
    groups, names = (OT_GROUPS, info["ot_groups"]) if testament == "ot" else (NT_GROUPS, info["nt_groups"])
    title = info[testament]
    lines = [f"<!-- reader: lang={info['voice']} -->", "",
             f"# {title} | {aligned(title, roman(title))} | {compare[testament]}", ""]
    for ((first, last), english), native in zip(groups, names):
        lines += [f"## {native} | {aligned(native, roman(native))} | {english}", "", "<!-- reader: table=glossary -->",
                  "| Name | Romanization | English |", "|---|---|---|"]
        for n in range(first, last + 1):
            name = info["books"][n - 1]
            lines.append(f"| {name} | {roman(name)} | {compare['book'](n)} |")
        lines.append("")
    return "\n".join(lines)


# English, compared with Chinese (the app's language): the Chinese name and its pinyin with each book.
ENGLISH = dict(name="English", ot="Books of the Old Testament", nt="Books of the New Testament")
CHINESE_TITLES = {"ot": ("旧约圣经书卷", "Jiù yuē shèng jīng shū juàn"), "nt": ("新约圣经书卷", "Xīn yuē shèng jīng shū juàn")}
CHINESE_GROUPS = {"ot": [("律法书", "Lǜ fǎ shū"), ("历史书", "Lì shǐ shū"), ("诗歌智慧书", "Shī gē zhì huì shū"),
                         ("大先知书", "Dà xiān zhī shū"), ("小先知书", "Xiǎo xiān zhī shū")],
                  "nt": [("福音书", "Fú yīn shū"), ("历史书", "Lì shǐ shū"), ("保罗书信", "Bǎo luó shū xìn"),
                         ("普通书信", "Pǔ tōng shū xìn"), ("预言书", "Yù yán shū")]}


def english_page(testament):
    """The English names, each with the Chinese name and its pinyin (bible/books/en-ot.md, -nt.md)."""
    groups = OT_GROUPS if testament == "ot" else NT_GROUPS
    chinese, pinyin = CHINESE_TITLES[testament]
    # No romanization line over English: the Chinese (with its pinyin) is the comparison.
    lines = ["<!-- reader: lang=en-US -->", "", f"# {ENGLISH[testament]} |  | {chinese} {pinyin}", ""]
    for ((first, last), english), (group, group_pinyin) in zip(groups, CHINESE_GROUPS[testament]):
        lines += [f"## {english} |  | {group} {group_pinyin}", "", "<!-- reader: table=glossary -->",
                  "| Name | Romanization | 中文 |", "|---|---|---|"]
        for n in range(first, last + 1):
            name, hanzi, reading, _ = bs.BOOKS[n - 1]
            lines.append(f"| {name} |  | {hanzi} {reading} |")
        lines.append("")
    return "\n".join(lines)


def readme_section(codes):
    """English first, then Chinese, then the other languages."""
    lines = ["### 书卷 Books of the Bible", ""]
    if "en" in codes:
        lines += ["#### English", "",
                  "- [Old Testament](books/en-ot.md)",
                  "- [New Testament](books/en-nt.md)", ""]
    lines += ["#### 中文 Chinese", "",
              "- [旧约 Old Testament](01-jiu-yue-shu-juan.md)",
              "- [新约 New Testament](02-xin-yue-shu-juan.md)", ""]
    for code in codes:
        if code == "en":
            continue
        info = LANGUAGES[code]
        lines += [f"#### {info['name']}", "",
                  f"- [{info['ot']} · Old Testament](books/{code}-ot.md)",
                  f"- [{info['nt']} · New Testament](books/{code}-nt.md)", ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--languages", default=",".join(ORDER), help=f"comma-separated (default {','.join(ORDER)})")
    p.add_argument("--compare", default="en", choices=sorted(COMPARE), help="the comparison language")
    p.add_argument("--text-repo", default=bp.default_text_repo(), help="the ChineseReaderText folder")
    a = p.parse_args()
    codes = [c.strip() for c in a.languages.split(",") if c.strip()]
    for code in codes:
        if code == "en":
            continue
        if code not in LANGUAGES:
            p.error(f"unknown language: {code} (known: {', '.join(ORDER)})")
        assert len(LANGUAGES[code]["books"]) == 66, (code, len(LANGUAGES[code]["books"]))
    out = os.path.join(a.text_repo, "bible", "books")
    os.makedirs(out, exist_ok=True)
    for code in codes:
        for testament in ("ot", "nt"):
            text = english_page(testament) if code == "en" else page(code, LANGUAGES[code], testament, COMPARE[a.compare])
            with open(os.path.join(out, f"{code}-{testament}.md"), "w", encoding="utf-8") as f:
                f.write(text + "\n")
    readme = os.path.join(a.text_repo, "bible", "README.md")
    text = open(readme, encoding="utf-8").read()
    # Replace everything from the Books heading up to the Passages heading.
    section = readme_section(codes)
    # The Naskapi lists come from workspace_naskapi (scripts/naskapi_book_lists.py): keep them listed.
    if os.path.exists(os.path.join(out, "nsk-ot.md")):
        section += "\n#### Naskapi\n\n- [Old Testament](books/nsk-ot.md)\n- [New Testament](books/nsk-nt.md)\n"
    text = re.sub(r"### 书卷 Books of the Bible\n.*?(?=### 经文 Passages)", lambda _: section + "\n",
                  text, count=1, flags=re.S)
    with open(readme, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {2 * len(codes)} page(s) to bible/books/ and the Books of the Bible section of bible/README.md")


if __name__ == "__main__":
    main()
