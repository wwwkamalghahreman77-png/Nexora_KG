"""
وارد کردن داده‌ی واقعی ایستگاه‌ها و کدهای HS که خودت جمع کردی.

استفاده:
    python -m database.import_data --stations stations.csv --cargo cargo.csv

فرمت CSV ایستگاه‌ها (ستون‌های ضروری: name_fa, country ؛ بقیه اختیاری):
    code,name_fa,name_en,name_ru,name_local,country,is_border_crossing,trade_role,aliases
    756905,سرخس,Serakhs,Серахс,,ترکمنستان,true,transit,"سرخس ترکمنستان"

فرمت CSV کالاها (ستون‌های ضروری: hs6_code, name_fa):
    hs6_code,full_code,name_fa,aliases
    721310,72131010,میلگرد,"آرماتور,میله فولادی"

اگه فایل خروجی سایت یا هر منبع دیگه‌ای ستون‌های متفاوتی داره، همین اسکریپت
رو راحت میشه ویرایش کرد - فقط اسم ستون‌ها تو COLUMN MAPPING پایین رو عوض کن.
"""
import argparse
import csv
from database.db import get_session, init_db
from database.models import Station, CargoType, RailConnection


def _to_bool(val: str) -> bool:
    return str(val).strip().lower() in ("1", "true", "yes", "بله", "verified", "✅")


def import_stations(path: str):
    db = get_session()
    added, updated = 0, 0
    try:
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name_fa = (row.get("name_fa") or "").strip()
                country = (row.get("country") or "").strip()
                if not name_fa or not country:
                    continue  # ردیف ناقص، رد میشه

                code = (row.get("code") or "").strip() or None
                # اگه ستون code_verified صراحتاً تو فایل باشه همونو ملاک قرار بده
                # (مثلاً داده‌ای که با OCR/ابزار خودکار استخراج شده باید False باشه
                # حتی اگه یک کد داره - چون ممکنه اشتباه خونده شده باشه)
                if "code_verified" in row:
                    verified_flag = _to_bool(row.get("code_verified", ""))
                else:
                    verified_flag = bool(code)

                existing = db.query(Station).filter(
                    Station.name_fa == name_fa, Station.country == country
                ).first()

                if existing:
                    if code:
                        existing.code = code
                        existing.code_verified = verified_flag
                    existing.name_en = row.get("name_en") or existing.name_en
                    existing.name_ru = row.get("name_ru") or existing.name_ru
                    existing.name_local = row.get("name_local") or existing.name_local
                    existing.trade_role = row.get("trade_role") or existing.trade_role
                    updated += 1
                else:
                    db.add(Station(
                        code=code,
                        name_fa=name_fa,
                        name_en=row.get("name_en") or None,
                        name_ru=row.get("name_ru") or None,
                        name_local=row.get("name_local") or None,
                        country=country,
                        is_border_crossing=_to_bool(row.get("is_border_crossing", "")),
                        trade_role=row.get("trade_role") or None,
                        aliases=row.get("aliases") or None,
                        code_verified=verified_flag,
                    ))
                    added += 1

        db.commit()
        print(f"ایستگاه‌ها: {added} اضافه، {updated} به‌روزرسانی شد.")
    finally:
        db.close()


def import_cargo(path: str):
    db = get_session()
    added, updated = 0, 0
    try:
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name_fa = (row.get("name_fa") or "").strip()
                hs6 = (row.get("hs6_code") or "").strip()
                if not name_fa or not hs6:
                    continue

                existing = db.query(CargoType).filter(CargoType.name_fa == name_fa).first()
                if existing:
                    existing.hs6_code = hs6
                    existing.full_code = row.get("full_code") or existing.full_code
                    existing.aliases = row.get("aliases") or existing.aliases
                    updated += 1
                else:
                    db.add(CargoType(
                        hs6_code=hs6,
                        full_code=row.get("full_code") or None,
                        name_fa=name_fa,
                        aliases=row.get("aliases") or None,
                    ))
                    added += 1

        db.commit()
        print(f"کالاها: {added} اضافه، {updated} به‌روزرسانی شد.")
    finally:
        db.close()


def import_connections(path: str):
    """
    فرمت CSV اتصالات (خطوط ریلی مستقیم بین دو ایستگاه):
        from_name_fa,from_country,to_name_fa,to_country,distance_km,corridor_name,is_operational
        سرخس,ایران,سرخس,ترکمنستان,3,کریدور شمال-جنوب,true

    فقط خطوطی که واقعاً می‌دونی عملیاتی‌ان رو با is_operational=true وارد کن؛
    برای خطوط در دست ساخت (مثل کاشغر-اوش) false بذار تا موتور مسیریابی
    اشتباهی پیشنهادشون نکنه.
    """
    db = get_session()
    added, skipped = 0, 0
    try:
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                origin = db.query(Station).filter(
                    Station.name_fa == row.get("from_name_fa", "").strip(),
                    Station.country == row.get("from_country", "").strip(),
                ).first()
                dest = db.query(Station).filter(
                    Station.name_fa == row.get("to_name_fa", "").strip(),
                    Station.country == row.get("to_country", "").strip(),
                ).first()

                if not origin or not dest:
                    skipped += 1
                    continue

                distance = row.get("distance_km")
                db.add(RailConnection(
                    from_station_id=origin.id,
                    to_station_id=dest.id,
                    distance_km=float(distance) if distance else None,
                    corridor_name=row.get("corridor_name") or None,
                    is_operational=_to_bool(row.get("is_operational", "true")),
                ))
                added += 1

        db.commit()
        print(f"اتصالات ریلی: {added} اضافه شد، {skipped} رد شد (ایستگاه پیدا نشد).")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stations", help="مسیر فایل CSV ایستگاه‌ها")
    parser.add_argument("--cargo", help="مسیر فایل CSV کالاها")
    parser.add_argument("--connections", help="مسیر فایل CSV اتصالات ریلی (برای موتور مسیریابی)")
    args = parser.parse_args()

    init_db()
    if args.stations:
        import_stations(args.stations)
    if args.cargo:
        import_cargo(args.cargo)
    if args.connections:
        import_connections(args.connections)
