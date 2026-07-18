"""
جستجوی فازی نام ایستگاه/کالا. عمداً از کتابخانه استاندارد پایتون (difflib)
استفاده شده تا هیچ وابستگی اضافه‌ای لازم نباشه.

منطق: هر رکورد (ایستگاه یا کالا) چند «کلید جستجو» داره: نام فارسی، نام
انگلیسی، نام محلی، و لیست مترادف‌ها (aliases). ورودی کاربر با تمام این
کلیدها مقایسه می‌شه و بهترین تطابق‌ها برگردونده می‌شه - حتی اگر غلط املایی
داشته باشه یا کامل ننوشته باشه.
"""
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional
from sqlalchemy.orm import Session
from Database.models import Station, CargoType

# نگاشت حروف فارسی/عربی به معادل لاتین تقریبی. چون خیلی از رکوردهای دیتابیس
# فعلاً فقط نام انگلیسی دارن (تا وقتی ترجمه‌ی کامل انجام بشه)، وقتی کاربر
# فارسی تایپ می‌کنه، این تابع ورودی رو به یک تلفظ لاتین تقریبی تبدیل می‌کنه
# تا بشه با نام انگلیسی مقایسه‌ی فازی کرد (مثلاً «سرخس» -> «srkhs» که به
# «Sarahs» به‌اندازه‌ی کافی شبیهه).
_FA_TO_LATIN = {
    "آ": "a", "ا": "a", "ب": "b", "پ": "p", "ت": "t", "ث": "s", "ج": "j",
    "چ": "ch", "ح": "h", "خ": "kh", "د": "d", "ذ": "z", "ر": "r", "ز": "z",
    "ژ": "zh", "س": "s", "ش": "sh", "ص": "s", "ض": "z", "ط": "t", "ظ": "z",
    "ع": "", "غ": "gh", "ف": "f", "ق": "gh", "ک": "k", "ك": "k", "گ": "g",
    "ل": "l", "م": "m", "ن": "n", "و": "v", "ه": "h", "ة": "h", "ی": "y",
    "ي": "y", "ئ": "y", "ء": "", "‌": " ",
}


def _has_persian(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text)


def _transliterate_fa_to_latin(text: str) -> str:
    return "".join(_FA_TO_LATIN.get(ch, ch) for ch in text)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def _normalize_for_match(text: str) -> str:
    """حذف پرانتز و علائم اضافه (مثل «(exp.)» تو داده‌های خام) قبل از مقایسه،
    تا این‌جور پسوندها امتیاز شباهت رو مصنوعی پایین نیارن."""
    import re
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[.,/_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _station_search_keys(s: Station) -> List[str]:
    keys = [s.name_fa]
    if s.name_en:
        keys.append(s.name_en)
    if s.name_ru:
        keys.append(s.name_ru)
    if s.name_local:
        keys.append(s.name_local)
    if s.aliases:
        keys.extend([a.strip() for a in s.aliases.split(",") if a.strip()])
    if s.code:
        keys.append(s.code)
    return keys


def _cargo_search_keys(c: CargoType) -> List[str]:
    keys = [c.name_fa, c.hs6_code]
    if c.full_code:
        keys.append(c.full_code)
    if c.aliases:
        keys.extend([a.strip() for a in c.aliases.split(",") if a.strip()])
    return keys


@dataclass
class StationMatch:
    station: Station
    score: float


@dataclass
class CargoMatch:
    cargo: CargoType
    score: float


def search_stations(db: Session, query: str, limit: int = 5, min_score: float = 0.45) -> List[StationMatch]:
    query = query.strip()
    if not query:
        return []

    q_l = query.lower()
    q_norm = _normalize_for_match(query)
    q_translit = _transliterate_fa_to_latin(query).lower() if _has_persian(query) else None
    q_translit_norm = _normalize_for_match(q_translit) if q_translit else None

    results: List[StationMatch] = []
    for station in db.query(Station).all():
        # تطابق زیررشته‌ای (شامل بودن) امتیاز بالایی می‌گیرد؛ در غیر این صورت شباهت رشته‌ای
        best = 0.0
        for key in _station_search_keys(station):
            if not key:
                continue
            key_l = key.lower()
            key_norm = _normalize_for_match(key)
            if q_l in key_l or key_l in q_l:
                best = max(best, 0.9)
            else:
                best = max(best, _similarity(q_norm, key_norm))
            if q_translit:
                if q_translit in key_l or key_l in q_translit:
                    best = max(best, 0.85)
                else:
                    best = max(best, _similarity(q_translit_norm, key_norm))
        if best >= min_score:
            results.append(StationMatch(station=station, score=best))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def search_cargo(db: Session, query: str, limit: int = 5, min_score: float = 0.45) -> List[CargoMatch]:
    query = query.strip()
    if not query:
        return []

    q_l = query.lower()
    q_norm = _normalize_for_match(query)
    q_translit = _transliterate_fa_to_latin(query).lower() if _has_persian(query) else None
    q_translit_norm = _normalize_for_match(q_translit) if q_translit else None

    results: List[CargoMatch] = []
    for cargo in db.query(CargoType).all():
        best = 0.0
        for key in _cargo_search_keys(cargo):
            if not key:
                continue
            key_l = key.lower()
            key_norm = _normalize_for_match(key)
            if q_l in key_l or key_l in q_l:
                best = max(best, 0.9)
            else:
                best = max(best, _similarity(q_norm, key_norm))
            if q_translit:
                if q_translit in key_l or key_l in q_translit:
                    best = max(best, 0.85)
                else:
                    best = max(best, _similarity(q_translit_norm, key_norm))
        if best >= min_score:
            results.append(CargoMatch(cargo=cargo, score=best))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
