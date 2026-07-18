from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from Database.Db import get_session
from Database.models import Partner, TariffDataPoint

router = Router()


class RegisterStates(StatesGroup):
    company_name = State()
    phone = State()


class SubmitTariffStates(StatesGroup):
    origin = State()
    dest = State()
    cargo = State()
    wagon = State()
    weight = State()
    price = State()


@router.callback_query(F.data == "partner_register")
async def partner_register_start(callback: CallbackQuery, state: FSMContext):
    db = get_session()
    try:
        existing = db.query(Partner).filter(
            Partner.telegram_user_id == callback.from_user.id
        ).first()
        if existing:
            status = "تایید شده ✅" if existing.verified else "در انتظار تایید ⏳"
            await callback.message.edit_text(
                f"شرکت «{existing.company_name}» قبلاً ثبت شده. وضعیت: {status}\n"
                f"پلن فعلی: {existing.tier} | اعتبار لید رایگان: {existing.lead_credits}"
            )
            return
    finally:
        db.close()

    await state.set_state(RegisterStates.company_name)
    await callback.message.edit_text("🏢 نام شرکت رو بفرست:")


@router.message(RegisterStates.company_name)
async def register_company_name(message: Message, state: FSMContext):
    await state.update_data(company_name=message.text.strip())
    await state.set_state(RegisterStates.phone)
    await message.answer("📞 شماره تماس شرکت رو بفرست:")


@router.message(RegisterStates.phone)
async def register_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    db = get_session()
    try:
        partner = Partner(
            company_name=data["company_name"],
            telegram_user_id=message.from_user.id,
            contact_phone=message.text.strip(),
            verified=False,
            tier="free",
            lead_credits=3,
        )
        db.add(partner)
        db.commit()
        await message.answer(
            "✅ ثبت‌نام انجام شد. درخواستت برای ادمین ارسال شد و بعد از تایید، "
            "شروع می‌کنی به دریافت لید. برای شروع، تعرفه‌های واقعی مسیرهایی که "
            "قبلاً حمل کردی رو با دستور /submit_tariff ثبت کن تا اولویت لید بگیری."
        )
    finally:
        db.close()
        await state.clear()


@router.message(Command("submit_tariff"))
async def submit_tariff_start(message: Message, state: FSMContext):
    db = get_session()
    try:
        partner = db.query(Partner).filter(
            Partner.telegram_user_id == message.from_user.id
        ).first()
        if not partner:
            await message.answer("اول باید شرکتت رو با /start → «ثبت شرکت» ثبت کنی.")
            return
    finally:
        db.close()

    await state.set_state(SubmitTariffStates.origin)
    await message.answer("📍 کد ایستگاه مبدأ این نمونه تعرفه رو بفرست:")


@router.message(SubmitTariffStates.origin)
async def st_origin(message: Message, state: FSMContext):
    await state.update_data(origin=message.text.strip())
    await state.set_state(SubmitTariffStates.dest)
    await message.answer("📍 کد ایستگاه مقصد:")


@router.message(SubmitTariffStates.dest)
async def st_dest(message: Message, state: FSMContext):
    await state.update_data(dest=message.text.strip())
    await state.set_state(SubmitTariffStates.cargo)
    await message.answer("📦 کد کالا (ETSNG/HS):")


@router.message(SubmitTariffStates.cargo)
async def st_cargo(message: Message, state: FSMContext):
    await state.update_data(cargo=message.text.strip())
    await state.set_state(SubmitTariffStates.wagon)
    await message.answer("🚃 نوع واگن (مثلاً مسقف):")


@router.message(SubmitTariffStates.wagon)
async def st_wagon(message: Message, state: FSMContext):
    await state.update_data(wagon=message.text.strip())
    await state.set_state(SubmitTariffStates.weight)
    await message.answer("⚖️ وزن بار (تن):")


@router.message(SubmitTariffStates.weight)
async def st_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.strip())
    except ValueError:
        await message.answer("فقط عدد بفرست.")
        return
    await state.update_data(weight=weight)
    await state.set_state(SubmitTariffStates.price)
    await message.answer("💰 مبلغ کل کرایه به دلار برای این محموله رو بفرست:")


@router.message(SubmitTariffStates.price)
async def st_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
    except ValueError:
        await message.answer("فقط عدد بفرست.")
        return

    data = await state.get_data()
    db = get_session()
    try:
        partner = db.query(Partner).filter(
            Partner.telegram_user_id == message.from_user.id
        ).first()

        dp = TariffDataPoint(
            origin_code=data["origin"],
            dest_code=data["dest"],
            cargo_code=data["cargo"],
            wagon_type=data["wagon"],
            weight_tons=data["weight"],
            price_usd=price,
            price_unit="total",
            partner_id=partner.id,
        )
        db.add(dp)
        partner.data_points_contributed += 1
        db.commit()

        await message.answer(
            f"✅ ثبت شد. مجموع نمونه‌های تعرفه شرکتت: {partner.data_points_contributed}\n"
            f"هرچی بیشتر ثبت کنی، اولویت دریافت لید در مسیرهای مشابه بالاتر میره."
        )
    finally:
        db.close()
        await state.clear()
