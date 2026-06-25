"""Генерация уникальных имён растения и транслитерация сортов (ТЗ №2/№3).

`lat_name_unique` = «род вид сорт» на латыни (чистая склейка).
`rus_name_unique` = «род-рус вид-рус» + сорт в русской транскрипции.

Транслитерация латиницы → русская практическая транскрипция — НЕидеальна по
определению (имена сортов), поэтому массовый прогон делается командой
`backfill_names` с dry-run и ручной вычиткой перед применением.
"""
import re

# Диграфы/сочетания — заменяем ДО одиночных букв (длинные первыми).
_DIGRAPHS = [
    ("shch", "щ"), ("sch", "ш"), ("tch", "ч"), ("sh", "ш"), ("ch", "ч"),
    ("ph", "ф"), ("th", "т"), ("ck", "к"), ("kh", "х"), ("zh", "ж"), ("wh", "в"),
    ("ts", "ц"), ("qu", "кв"), ("ya", "я"), ("yo", "ё"), ("yu", "ю"),
    ("ye", "е"), ("ay", "эй"), ("ey", "ей"), ("oy", "ой"), ("ai", "ай"),
    ("ei", "ей"), ("au", "ау"), ("ou", "у"), ("ow", "оу"), ("ee", "и"),
    ("oo", "у"),
]
_SINGLE = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х",
    "i": "и", "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "п", "q": "к", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "w": "в", "x": "кс", "y": "и", "z": "з",
}


def _translit_word(word: str) -> str:
    low = word.lower()
    out = []
    i = 0
    n = len(low)
    while i < n:
        # диграфы — ПЕРВЫМИ (иначе 'c' перехватит 'ch' и т.п.)
        matched = False
        for src, dst in _DIGRAPHS:
            if low.startswith(src, i):
                out.append(dst)
                i += len(src)
                matched = True
                break
        if matched:
            continue
        ch = low[i]
        # 'c' мягкая перед e/i/y → «с», иначе «к»
        if ch == "c":
            nxt = low[i + 1] if i + 1 < n else ""
            out.append("с" if nxt in "eiy" else "к")
            i += 1
            continue
        out.append(_SINGLE.get(ch, ch))  # не-латиница (цифры, кириллица, симв.) — как есть
        i += 1
    res = "".join(out)
    return res[:1].upper() + res[1:] if res else res


# Диакритика европейских языков → базовая латиница (Paweł→Pawel, Söhne→Sohne).
_DIACRITICS = str.maketrans({
    "à": "a", "á": "a", "â": "a", "ä": "a", "ã": "a", "å": "a", "ā": "a",
    "ç": "c", "č": "c", "ć": "c", "è": "e", "é": "e", "ê": "e", "ë": "e",
    "ē": "e", "ě": "e", "ì": "i", "í": "i", "î": "i", "ï": "i", "ī": "i",
    "ñ": "n", "ń": "n", "ò": "o", "ó": "o", "ô": "o", "ö": "o", "õ": "o",
    "ø": "o", "ō": "o", "ù": "u", "ú": "u", "û": "u", "ü": "u", "ū": "u",
    "ý": "y", "ÿ": "y", "ż": "z", "ź": "z", "ž": "z", "š": "s", "ś": "s",
    "ł": "l", "đ": "d",
    "À": "A", "Á": "A", "Â": "A", "Ä": "A", "Å": "A", "Ç": "C", "É": "E",
    "È": "E", "Ê": "E", "Ë": "E", "Í": "I", "Î": "I", "Ï": "I", "Ñ": "N",
    "Ó": "O", "Ô": "O", "Ö": "O", "Ø": "O", "Ú": "U", "Ü": "U", "Ż": "Z",
    "Ž": "Z", "Š": "S", "Ś": "S", "Ł": "L",
})
_ROMAN = re.compile(r"[IVXLCDM]{1,4}\Z")          # римские цифры (II, III, IV) — не трогаем
_WORD = re.compile(r"[A-Za-z][A-Za-z'’`]*")  # слово + притяжательное 's


def _token(mo: "re.Match") -> str:
    w = mo.group(0)
    return w if _ROMAN.match(w) else _translit_word(w)


def transliterate(text: str | None) -> str:
    """Латиница → русская транскрипция, по словам (разделители/цифры/кириллица как есть)."""
    if not text:
        return ""
    text = text.translate(_DIACRITICS)
    if not re.search(r"[A-Za-z]", text):
        return text.strip()
    return _WORD.sub(_token, text).strip()


def _join(*parts: str | None) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip()).strip()


def build_lat_name(genus_name, species_name, variety) -> str:
    """«Larix decidua Kornik» — латинская склейка рода/вида/сорта."""
    return _join(genus_name, species_name, variety)


def build_rus_name(genus_rus, species_rus, variety) -> str:
    """«Лиственница европейская Корник» — рус. род/вид + сорт в транскрипции."""
    return _join(genus_rus, species_rus, transliterate(variety))
