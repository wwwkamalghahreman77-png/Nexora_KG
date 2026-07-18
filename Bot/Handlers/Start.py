from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

router = Router()


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚂 محاسبه سریع تعرفه", callback_data="calc_start")],
        [InlineKeyboardButton(text="🔎 جستجوی کد ایستگاه / کالا", callback_data="lookup_station")],
        [InlineKeyboardButton(text="🗺 مسیریابی حمل", callback_data="route_start")],
        [InlineKeyboardButton(text="🏢 ثبت شرکت (رایگان)", callback_data="partner_register")],
        [InlineKeyboardButton(text="ℹ️ درباره شبکه", callback_data="about")],
    ])


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 به <b>شبکه تعرفه مشترک ریلی CIS</b> خوش اومدی!\n\n"
        "این ربات بر پایه‌ی داده‌های واقعی که شرکت‌های حمل‌ونقل عضو به‌صورت داوطلبانه "
        "ثبت می‌کنن، تعرفه تقریبی حمل ریلی رو بهت میده - کاملاً رایگان.\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧠 <b>چطور کار می‌کنه؟</b>\n\n"
        "شرکت‌های حمل‌ونقل عضو، نمونه تعرفه‌های واقعی مسیرهای خودشون رو ثبت می‌کنن. "
        "ربات از میانگین این داده‌ها تخمین می‌زنه. هرچی داده بیشتر بشه، تخمین دقیق‌تر میشه.\n\n"
        "شرکت‌ها در ازای ثبت داده، لید (مشتری واقعی) از ربات می‌گیرن.\n"
        "برای مسیرهای بدون داده، درخواستت مستقیم به شرکت‌های عضو ارسال میشه.",
        reply_markup=main_menu_kb(),
    )
