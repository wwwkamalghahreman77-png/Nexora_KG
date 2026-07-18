"""
نقطه ورود ربات. اجرا: python -m bot.main
پیش‌نیاز: BOT_TOKEN را در فایل .env یا متغیر محیطی قرار بده.
"""
import asyncio
import logging
import os

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from Database.Db import init_db
from Bot.Handlers import Start as start, calculate, partner, admin, station_lookup, route_planner

logging.basicConfig(level=logging.INFO)


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN تنظیم نشده. آن را در .env قرار بده.")

    init_db()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(calculate.router)
    dp.include_router(partner.router)
    dp.include_router(admin.router)
    dp.include_router(station_lookup.router)
    dp.include_router(route_planner.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
