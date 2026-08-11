import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import database as db
from handlers.common import router as common_router
from handlers.user import router as user_router
from handlers.support import router as support_router
from handlers.admin import router as admin_router

async def main():
    await db.init_db()
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(common_router)
    dp.include_router(user_router)
    dp.include_router(support_router)
    dp.include_router(admin_router)
    print("Bot started.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
