from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from config import ADMIN_IDS
import database as db
from keyboards.user import user_main
from keyboards.admin import admin_main
import json

router = Router()

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await db.upsert_user(message.from_user)
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "Добро пожаловать, ваше высочество 👑\n\n"
            "Панель управления жалкими смертными к вашим услугам.\n\n"
            "Что сегодня будем делать?",
            reply_markup=admin_main()
        )
    elif await db.is_banned(message.from_user.id):
        await message.answer(
            "Доступ к боту ограничен администрацией.\n\n"
            "Если считаешь, что произошла ошибка, обратись к администрации."
        )
    else:
        app = await db.get_user_application(message.from_user.id)
        member = bool(app and app[4] == "approved")
        await message.answer(
            ("Привет снова! Рады видеть тебя во флуде 🫶" if member else "Приветствую! 🫶\n\nРады видеть тебя здесь.")
            + "\n\nВыбери, чем займёмся:",
            reply_markup=user_main(member)
        )

@router.message(F.text == "↩️ Назад")
async def back(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Возвращаемся в панель управления 👑", reply_markup=admin_main())
    else:
        await message.answer("Возвращаемся в главное меню 🫶", reply_markup=user_main())
