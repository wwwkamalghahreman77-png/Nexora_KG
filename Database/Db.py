"""
اتصال به دیتابیس. برای شروع از SQLite استفاده می‌کنیم (نیازی به سرور جدا نیست).
وقتی تعداد شرکت‌های عضو و ترافیک بالا رفت، فقط DATABASE_URL را به
PostgreSQL تغییر بده - بقیه کد دست‌نخورده می‌ماند.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///rail_network.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """ساخت جداول در اولین اجرا"""
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
