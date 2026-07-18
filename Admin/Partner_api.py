import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from Database.Db import get_session
from Database.models import Partner, TariffDataPoint, Lead, Station

router = Router()

ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("add_station"))
async def add_station(message: Message):
    """
    استفاده: /add_station <کد> <نام‌فارسی> <کشور>
    برای ثبت یا تایید کد یک ایستگاه که قبلاً بدون کد در دیتابیس بوده.
    مثال: /add_station 756905 سرخس ترکمنستان
    """
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) != 4:
        await message.answer("فرمت: /add_station <کد> <نام‌فارسی> <کشور>")
        return

    _, code, name_fa, country = parts
    db = get_session()
    try:
        station = db.query(Station).filter(
            Station.name_fa == name_fa, Station.country == country
        ).first()
        if station:
            station.code = code
            station.code_verified = True
        else:
            station = Station(
                name_fa=name_fa, country=country, code=code, code_verified=True
            )
            db.add(station)
        db.commit()
        await message.answer(f"✅ کد {code} برای «{name_fa} - {country}» ثبت/تایید شد.")
    finally:
        db.close()


@router.message(Command("approve"))
async def approve_partner(message: Message):
    """استفاده: /approve <partner_id>"""
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("فرمت: /approve <partner_id>")
        return

    db = get_session()
    try:
        partner = db.query(Partner).get(int(parts[1]))
        if not partner:
            await message.answer("شرکتی با این آیدی پیدا نشد.")
            return
        partner.verified = True
        db.commit()
        await message.answer(f"✅ شرکت «{partner.company_name}» تایید شد.")
    finally:
        db.close()


@router.message(Command("set_tier"))
async def set_tier(message: Message):
    """استفاده: /set_tier <partner_id> <free|pro|enterprise>"""
    if not _is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 3 or parts[2] not in ("free", "pro", "enterprise"):
        await message.answer("فرمت: /set_tier <partner_id> <free|pro|enterprise>")
        return

    db = get_session()
    try:
        partner = db.query(Partner).get(int(parts[1]))
        if not partner:
            await message.answer("شرکتی با این آیدی پیدا نشد.")
            return
        partner.tier = parts[2]
        db.commit()
        await message.answer(f"✅ پلن «{partner.company_name}» به {parts[2]} تغییر کرد.")
    finally:
        db.close()


@router.message(Command("stats"))
async def stats(message: Message):
    if not _is_admin(message.from_user.id):
        return

    db = get_session()
    try:
        partners_count = db.query(Partner).count()
        verified_count = db.query(Partner).filter(Partner.verified.is_(True)).count()
        data_points = db.query(TariffDataPoint).count()
        leads_count = db.query(Lead).count()

        await message.answer(
            f"📊 <b>آمار شبکه</b>\n\n"
            f"شرکت‌های ثبت‌شده: {partners_count}\n"
            f"شرکت‌های تاییدشده: {verified_count}\n"
            f"نمونه‌های تعرفه ثبت‌شده: {data_points}\n"
            f"کل لیدهای تولیدشده: {leads_count}"
        )
    finally:
        db.close()
