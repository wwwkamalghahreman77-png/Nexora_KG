"""
بخش مستقل «جستجوی کد ایستگاه/کالا».
کاربر می‌تونه اسم ناقص یا با غلط املایی وارد کنه (مثلاً «آهنگران»)،
ربات نزدیک‌ترین ایستگاه‌ها رو با نام فارسی، انگلیسی، محلی و کد پیدا می‌کنه.
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from Database.Db import get_session
from Core.fuzzy_search import search_stations, search_cargo

router = Router()


class LookupStates(StatesGroup):
    waiting_query = State()


@router.callback_query(F.data == "lookup_station")
@router.message(Command("station"))
async def lookup_start(event, state: FSMContext):
    await state.set_state(LookupStates.waiting_query)
    text = (
        "🔎 اسم یا بخشی از اسم ایستگاه رو بفرست (فارسی، انگلیسی یا حتی با غلط "
        "املایی مشکلی نداره - مثلاً «سرخس» یا «آهنگران»).\n\n"
        "برای جستجوی کد کالا هم کافیه اسم کالا رو بفرستی (مثلاً «میلگرد»)."
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text)
    else:
        await event.answer(text)


@router.message(LookupStates.waiting_query)
async def lookup_query(message: Message, state: FSMContext):
    query = message.text.strip()
    db = get_session()
    try:
        station_matches = search_stations(db, query)
        cargo_matches = search_cargo(db, query)

        if not station_matches and not cargo_matches:
            await message.answer(
                "چیزی پیدا نشد. هجی دیگه‌ای امتحان کن، یا اگه مطمئنی این ایستگاه/کالا "
                "وجود داره ولی تو دیتابیس نیست، به ادمین شبکه اطلاع بده تا اضافه‌ش کنه."
            )
            return

        if station_matches:
            lines = ["🚉 <b>نتایج ایستگاه</b>\n"]
            for m in station_matches:
                s = m.station
                code_text = s.code if s.code else "❓ کد هنوز تایید نشده"
                verified = " ✅" if s.code_verified else " (نیاز به تایید)" if s.code else ""
                role_map = {"import": "واردات 📥", "export": "صادرات 📤", "both": "واردات و صادرات 🔁", "transit": "ترانزیت 🔄"}
                role_text = f" | نقش: {role_map.get(s.trade_role, 'نامشخص')}" if s.trade_role else ""
                lines.append(
                    f"• <b>{s.name_fa}</b>"
                    + (f" / {s.name_en}" if s.name_en else "")
                    + (f" / {s.name_ru}" if s.name_ru else "")
                    + (f" / {s.name_local}" if s.name_local else "")
                    + f"\n  کشور: {s.country} | کد: {code_text}{verified}{role_text}\n"
                )
            await message.answer("\n".join(lines))

        if cargo_matches:
            lines = ["📦 <b>نتایج کالا</b>\n"]
            for m in cargo_matches:
                c = m.cargo
                full = f" | کد کامل: {c.full_code}" if c.full_code else ""
                lines.append(f"• <b>{c.name_fa}</b>\n  کد HS: {c.hs6_code}{full}\n")
            await message.answer("\n".join(lines))

    finally:
        db.close()
        await state.clear()
