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


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


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

    results: List[StationMatch] = []
    for station in db.query(Station).all():
        # تطابق زیررشته‌ای (شامل بودن) امتیاز بالایی می‌گیرد؛ در غیر این صورت شباهت رشته‌ای
        best = 0.0
        for key in _station_search_keys(station):
            if not key:
                continue
            key_l = key.lower()
            q_l = query.lower()
            if q_l in key_l or key_l in q_l:
                best = max(best, 0.9)
            else:
                best = max(best, _similarity(query, key))
        if best >= min_score:
            results.append(StationMatch(station=station, score=best))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def search_cargo(db: Session, query: str, limit: int = 5, min_score: float = 0.45) -> List[CargoMatch]:
    query = query.strip()
    if not query:
        return []

    results: List[CargoMatch] = []
    for cargo in db.query(CargoType).all():
        best = 0.0
        for key in _cargo_search_keys(cargo):
            if not key:
                continue
            key_l = key.lower()
            q_l = query.lower()
            if q_l in key_l or key_l in q_l:
                best = max(best, 0.9)
            else:
                best = max(best, _similarity(query, key))
        if best >= min_score:
            results.append(CargoMatch(cargo=cargo, score=best))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
