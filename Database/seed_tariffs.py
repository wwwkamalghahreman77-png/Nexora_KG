"""
اجرا: python -m database.seed_tariffs

⚠️ نکته مهم درباره دقت داده‌ها:
کدهای عددی ایستگاه‌ها (مثل ۷۵۶۹۰۵) از سامانه‌ی کدگذاری شبکه‌ی راه‌آهن‌های
CIS/OSJD میان که یک منبع رسمی و زنده لازم داره (نه چیزی که بشه از حافظه
یا جستجوی وب با اطمینان کامل تولید کرد). برای همین:
  - فقط کدهایی که خودِ کاربر/شرکت‌های عضو تایید کرده‌اند، code_verified=True
    و شماره‌دار ثبت شده‌اند (سرخس‌ترکمنستان، عینی‌تاجیکستان).
  - بقیه‌ی ایستگاه‌های مرزی ایران (که در منابع عمومی به عنوان مرز ریلی رسمی
    شناخته شده‌اند) با نام درست ثبت شده‌اند ولی code=None تا کسی کد اشتباه
    رو در محاسبات استفاده نکنه. این کدها رو باید از طریق شرکت‌های عضو
    (دستور /submit_tariff یا یک ابزار ادمین جدید) یا مدارک رسمی راه‌آهن
    تکمیل کنید - نه با حدس.
  - کدهای HS کالاها فقط در سطح ۶ رقمی جهانی (استاندارد و قابل‌اتکا) وارد
    شده‌اند؛ کد کامل ۸-۱۰ رقمی (مثل ETSNG یا تعرفه گمرکی داخلی) را هرکشور
    خودش تعیین می‌کند و باید توسط شرکت‌های عضو یا منبع رسمی تکمیل شود.

این فایل رو هر وقت داده‌ی تاییدشده‌ی جدید داشتی، گسترش بده.
"""
from Database.Db import get_session, init_db
from Database.models import Station, CargoType


# (name_fa, name_en, name_local, country, code, code_verified, is_border_crossing, aliases)
SEED_STATIONS = [
    # --- مرزهای رسمی ریلی ایران با کشورهای همسایه ---
    ("سرخس", "Sarakhs", None, "ایران", None, False, True, "سرخس ایران,Sarakhs Iran"),
    ("سرخس", "Serakhs", None, "ترکمنستان", "756905", True, True, "سرخس ترکمنستان,Serakhs Turkmenistan"),
    ("اینچه برون", "Incheh Borun", None, "ایران", None, False, True, "اینچه‌برون"),
    ("لطف‌آباد", "Lotfabad", None, "ایران", None, False, True, "لطف اباد"),
    ("شمتیغ", "Shamtigh", None, "ایران", None, False, True, None),
    ("جلفا", "Jolfa", None, "ایران", None, False, True, None),
    ("رازی", "Razi", None, "ایران", None, False, True, None),
    ("میرجاوه", "Mirjaveh", None, "ایران", None, False, True, None),
    # --- مقصد ثبت‌شده توسط کاربر ---
    ("عینی", "Ayni", None, "تاجیکستان", "745506", True, False, None),
]

# (hs6_code, full_code, name_fa, aliases)
SEED_CARGO = [
    ("721310", "72131010", "میلگرد", "آرماتور,میله فولادی"),
    ("720839", None, "ورق فولادی گرم‌نورد", "ورق گرم,hot rolled steel"),
    ("100199", None, "گندم", "wheat"),
    ("520100", None, "پنبه خام", "cotton"),
    ("252329", None, "سیمان", "cement"),
    ("260111", None, "سنگ آهن", "iron ore"),
    ("720839", None, "شمش فولادی (بیلت)", "بیلت,billet"),
]


def run():
    init_db()
    db = get_session()
    try:
        for name_fa, name_en, name_local, country, code, verified, is_border, aliases in SEED_STATIONS:
            exists = db.query(Station).filter(
                Station.name_fa == name_fa, Station.country == country
            ).first()
            if not exists:
                db.add(Station(
                    name_fa=name_fa, name_en=name_en, name_local=name_local,
                    country=country, code=code, code_verified=verified,
                    is_border_crossing=is_border, aliases=aliases,
                ))

        for hs6, full_code, name_fa, aliases in SEED_CARGO:
            exists = db.query(CargoType).filter(CargoType.name_fa == name_fa).first()
            if not exists:
                db.add(CargoType(hs6_code=hs6, full_code=full_code, name_fa=name_fa, aliases=aliases))

        db.commit()
        print("داده‌های اولیه با موفقیت اضافه شد.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
