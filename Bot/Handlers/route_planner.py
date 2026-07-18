from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.db import get_session
from core.fuzzy_search import search_stations
from core.route_engine import find_routes

router = Router()


class RouteStates(StatesGroup):
    origin = State()
    destination = State()


def _fmt_station(s) -> str:
    names = [s.name_fa]
    if s.name_en:
        names.append(s.name_en)
    if s.name_ru:
        names.append(s.name_ru)
    return " / ".join(names)


@router.callback_query(F.data == "route_start")
async def route_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RouteStates.origin)
    await callback.message.edit_text("🗺 اسم شهر/ایستگاه مبدأ رو بفرست:")


@router.message(RouteStates.origin)
async def route_origin(message: Message, state: FSMContext):
    db = get_session()
    try:
        matches = search_stations(db, message.text.strip(), limit=1)
        if not matches:
            await message.answer("این ایستگاه/شهر تو دیتابیس پیدا نشد. اسم دیگه‌ای امتحان کن:")
            return
        await state.update_data(origin_id=matches[0].station.id)
        await state.set_state(RouteStates.destination)
        await message.answer(
            f"مبدأ: {_fmt_station(matches[0].station)}\n\n🗺 حالا اسم شهر/ایستگاه مقصد رو بفرست:"
        )
    finally:
        db.close()


@router.message(RouteStates.destination)
async def route_destination(message: Message, state: FSMContext):
    db = get_session()
    try:
        matches = search_stations(db, message.text.strip(), limit=1)
        if not matches:
            await message.answer("این ایستگاه/شهر تو دیتابیس پیدا نشد. اسم دیگه‌ای امتحان کن:")
            return

        data = await state.get_data()
        origin = db.query(matches[0].station.__class__).get(data["origin_id"])
        destination = matches[0].station

        main_route, alt_route = find_routes(db, origin, destination)

        if not main_route:
            await message.answer(
                f"⚠️ برای مسیر {_fmt_station(origin)} → {_fmt_station(destination)} "
                f"هنوز خط ریلی عملیاتی و تاییدشده‌ای تو دیتابیس ثبت نشده.\n\n"
                f"این می‌تونه به این معنی باشه که مسیر کلاً ریلی مستقیم نداره "
                f"(نیاز به مسیر ترکیبی/جاده‌ای)، یا فقط هنوز داده‌ی این بخش از "
                f"شبکه وارد نشده. لطفاً با ادمین شبکه چک کن."
            )
            return

        text = "🚂 <b>مسیر اصلی</b>\n\n"
        text += " → ".join(_fmt_station(s) for s in main_route.stations)
        if main_route.total_distance_km:
            text += f"\n\n📏 مجموع فاصله: ~{main_route.total_distance_km:,.0f} کیلومتر"
        if main_route.corridors:
            text += f"\n🛤 کریدور: {', '.join(main_route.corridors)}"

        if alt_route:
            text += "\n\n🔀 <b>مسیر جایگزین</b>\n\n"
            text += " → ".join(_fmt_station(s) for s in alt_route.stations)
            if alt_route.total_distance_km:
                text += f"\n📏 مجموع فاصله: ~{alt_route.total_distance_km:,.0f} کیلومتر"

        await message.answer(text)

    finally:
        db.close()
        await state.clear()
