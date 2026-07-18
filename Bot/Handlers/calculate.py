from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_session
from database.models import Lead
from core.tariff_engine import estimate_tariff
from core.lead_matching import find_matching_partners, consume_lead_credit

router = Router()


class CalcStates(StatesGroup):
    origin = State()
    dest = State()
    cargo = State()
    wagon = State()
    weight = State()


WAGON_TYPES = ["مسقف", "لبه‌بلند", "لبه‌کوتاه", "پلتفرم", "مخزن‌دار"]


def wagon_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=w, callback_data=f"wagon:{w}")] for w in WAGON_TYPES]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "calc_start")
async def calc_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CalcStates.origin)
    await callback.message.edit_text(
        "📍 کد ایستگاه مبدأ رو بفرست (مثلاً 756905 برای سرخس):"
    )


@router.message(CalcStates.origin)
async def get_origin(message: Message, state: FSMContext):
    await state.update_data(origin=message.text.strip())
    await state.set_state(CalcStates.dest)
    await message.answer("📍 کد ایستگاه مقصد رو بفرست:")


@router.message(CalcStates.dest)
async def get_dest(message: Message, state: FSMContext):
    await state.update_data(dest=message.text.strip())
    await state.set_state(CalcStates.cargo)
    await message.answer("📦 کد کالا (ETSNG/HS) رو بفرست (مثلاً 72131010 برای میلگرد):")


@router.message(CalcStates.cargo)
async def get_cargo(message: Message, state: FSMContext):
    await state.update_data(cargo=message.text.strip())
    await state.set_state(CalcStates.wagon)
    await message.answer("🚃 نوع واگن رو انتخاب کن:", reply_markup=wagon_kb())


@router.callback_query(CalcStates.wagon, F.data.startswith("wagon:"))
async def get_wagon(callback: CallbackQuery, state: FSMContext):
    wagon = callback.data.split(":", 1)[1]
    await state.update_data(wagon=wagon)
    await state.set_state(CalcStates.weight)
    await callback.message.edit_text("⚖️ وزن بار به تن رو بفرست (مثلاً 67):")


@router.message(CalcStates.weight)
async def get_weight_and_calculate(message: Message, state: FSMContext, bot: Bot):
    try:
        weight = float(message.text.strip())
    except ValueError:
        await message.answer("لطفاً فقط عدد بفرست (مثلاً 67).")
        return

    data = await state.get_data()
    origin, dest, cargo, wagon = data["origin"], data["dest"], data["cargo"], data["wagon"]

    db = get_session()
    try:
        result = estimate_tariff(db, origin, dest, cargo, wagon, weight)

        lead = Lead(
            user_telegram_id=message.from_user.id,
            origin_code=origin,
            dest_code=dest,
            cargo_code=cargo,
            wagon_type=wagon,
            weight_tons=weight,
            estimated_price_usd=result.price_usd,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        if result.found:
            text = (
                f"📊 <b>تخمین تعرفه</b>\n\n"
                f"مسیر: {origin} → {dest}\n"
                f"کالا: {cargo} | واگن: {wagon} | وزن: {weight} تن\n\n"
                f"💰 برآورد: <b>~{result.price_usd:,.0f} دلار</b>\n"
                f"سطح اطمینان: {result.confidence}\n\n"
                f"{result.message}\n\n"
                f"⚠️ این یک برآورد از میانگین داده‌های شبکه است، نه فاکتور رسمی."
            )
        else:
            text = f"⚠️ {result.message}"

        await message.answer(text)

        # ارجاع لید به شرکت‌های عضو
        partners = find_matching_partners(db, origin, dest)
        if not partners:
            await message.answer(
                "فعلاً شرکت تاییدشده‌ای برای این مسیر عضو شبکه نیست. "
                "درخواستت ذخیره شد و به‌محض عضویت شرکت مرتبط، بهت اطلاع می‌دیم."
            )
        else:
            notified = 0
            for partner in partners:
                if consume_lead_credit(db, partner):
                    try:
                        await bot.send_message(
                            partner.telegram_user_id,
                            f"🔔 <b>درخواست جدید مشتری</b>\n\n"
                            f"مسیر: {origin} → {dest}\n"
                            f"کالا: {cargo} | واگن: {wagon} | وزن: {weight} تن\n\n"
                            f"برای تماس با مشتری به ادمین شبکه پیام بده و شماره لید "
                            f"#{lead.id} رو اعلام کن.",
                        )
                        notified += 1
                    except Exception:
                        pass  # شرکت بات رو بلاک کرده یا استارت نزده

            if notified:
                await message.answer(
                    f"✅ درخواستت برای {notified} شرکت عضو ارسال شد. "
                    f"به‌زودی از طریق ربات یا تماس مستقیم باهات هماهنگ می‌کنن."
                )

    finally:
        db.close()
        await state.clear()
