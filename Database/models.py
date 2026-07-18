"""
مدل‌های دیتابیس شبکه تعرفه مشترک ریلی CIS
SQLAlchemy ORM - قابل استفاده با SQLite (شروع) یا PostgreSQL (مقیاس بالاتر)
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Station(Base):
    """ایستگاه‌های راه‌آهن با کد بین‌المللی (مثل ۷۵۶۹۰۵ سرخس)"""
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=True, index=True)  # اگر هنوز تایید نشده، خالی می‌ماند
    name_fa = Column(String(120), nullable=False)
    name_en = Column(String(120))
    name_ru = Column(String(120))
    name_local = Column(String(120))       # نام به زبان محلی کشور مقصد/ایستگاه (اگر با روسی/انگلیسی فرق دارد)
    country = Column(String(60), nullable=False)
    is_border_crossing = Column(Boolean, default=False)
    trade_role = Column(String(20))        # import | export | both | transit | None (نامشخص)
    aliases = Column(Text)                 # نام‌های جایگزین/املای رایج، با کاما جدا (برای جستجوی فازی)
    code_verified = Column(Boolean, default=False)  # False یعنی کد هنوز از منبع رسمی تایید نشده


class RailConnection(Base):
    """
    یال گراف شبکه‌ی ریلی: یعنی بین دو ایستگاه/گره، خط ریلی عملیاتی مستقیم وجود دارد.
    موتور مسیریابی (core/route_engine.py) از مجموع این یال‌ها مسیر اصلی و
    جایگزین را پیدا می‌کند. عمداً فقط خطوطی که واقعاً تاییدشده و عملیاتی‌اند
    وارد می‌شوند - نه پروژه‌های در دست ساخت (وگرنه مسیر غلط پیشنهاد می‌شود).
    """
    __tablename__ = "rail_connections"

    id = Column(Integer, primary_key=True)
    from_station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    to_station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    distance_km = Column(Float, nullable=True)
    corridor_name = Column(String(150))    # مثلاً "کریدور شمال-جنوب" برای نمایش به کاربر
    is_operational = Column(Boolean, default=True)  # False = در دست ساخت / هنوز فعال نشده
    notes = Column(Text)


class CargoType(Base):
    """نوع کالا بر اساس کد HS بین‌المللی (۶ رقمی، جهانی) یا کد داخلی تعرفه‌ای دقیق‌تر"""
    __tablename__ = "cargo_types"

    id = Column(Integer, primary_key=True)
    hs6_code = Column(String(10), nullable=False, index=True)   # کد ۶ رقمی HS جهانی
    full_code = Column(String(20))          # کد کامل ETSNG/داخلی در صورت وجود (مثل 72131010)
    name_fa = Column(String(150), nullable=False)
    aliases = Column(Text)                  # مترادف‌ها برای جستجوی فازی


class Partner(Base):
    """شرکت‌های عضو شبکه (فورواردرها)"""
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True)
    company_name = Column(String(150), nullable=False)
    telegram_user_id = Column(Integer, unique=True, nullable=False)
    contact_phone = Column(String(30))
    verified = Column(Boolean, default=False)          # تایید توسط ادمین
    tier = Column(String(20), default="free")          # free | pro | enterprise
    lead_credits = Column(Integer, default=3)           # تعداد لید رایگان ماهانه
    data_points_contributed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    tariffs = relationship("TariffDataPoint", back_populates="partner")


class TariffDataPoint(Base):
    """
    هر رکورد یک نمونه واقعی تعرفه است که یک شرکت عضو ثبت کرده.
    موتور محاسبه (core/tariff_engine.py) از میانگین این رکوردها تخمین می‌زند.
    """
    __tablename__ = "tariff_data_points"

    id = Column(Integer, primary_key=True)
    origin_code = Column(String(10), nullable=False, index=True)
    dest_code = Column(String(10), nullable=False, index=True)
    cargo_code = Column(String(20), nullable=False, index=True)
    wagon_type = Column(String(40), nullable=False)     # مسقف، لبه‌بلند، پلتفرم، مخزن‌دار...
    weight_tons = Column(Float, nullable=False)
    price_usd = Column(Float, nullable=False)           # کل کرایه یا نرخ هر تن (price_unit مشخص می‌کند)
    price_unit = Column(String(10), default="total")    # total | per_ton
    partner_id = Column(Integer, ForeignKey("partners.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    partner = relationship("Partner", back_populates="tariffs")


class Lead(Base):
    """درخواست هر کاربر نهایی که به شرکت‌های عضو ارجاع داده می‌شود"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(Integer, nullable=False)
    origin_code = Column(String(10), nullable=False)
    dest_code = Column(String(10), nullable=False)
    cargo_code = Column(String(20), nullable=False)
    wagon_type = Column(String(40), nullable=False)
    weight_tons = Column(Float, nullable=False)
    estimated_price_usd = Column(Float)
    matched_partner_id = Column(Integer, ForeignKey("partners.id"), nullable=True)
    status = Column(String(20), default="new")   # new | sent | contacted | closed
    created_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    """اشتراک پولی شرکت‌ها (نمایش اولویت‌دار، آمار بازار، API)"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    plan = Column(String(20), nullable=False)     # pro | enterprise
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True)
