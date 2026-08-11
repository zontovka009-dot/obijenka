
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.support import SupportStates
from keyboards.user import user_main
import database as db

router=Router()

@router.message(F.text=="🆘 Поддержка")
async def support(message:Message,state:FSMContext):
    if await db.is_banned(message.from_user.id): return await message.answer("Доступ к боту ограничен администрацией.")
    kb=ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚖️ Апелляция наказания")],
        [KeyboardButton(text="⚠️ Жалоба"),KeyboardButton(text="💬 Другое")],
        [KeyboardButton(text="↩️ Назад")]],resize_keyboard=True)
    await message.answer("Выбери тип обращения 🫶",reply_markup=kb)
    await state.set_state(SupportStates.writing)

@router.message(SupportStates.writing)
async def support_writing(message:Message,state:FSMContext):
    if message.text=="↩️ Назад": await state.clear(); return await message.answer("Главное меню 🫶",reply_markup=user_main())
    types={"⚖️ Апелляция наказания":"Апелляция наказания","⚠️ Жалоба":"Жалоба","💬 Другое":"Другое"}
    if message.text in types:
        prompts={
            "Апелляция наказания":"Здравствуйте! 🫶 Укажи причину наказания, свою роль и подробно опиши суть обращения.",
            "Жалоба":"Добрый день! Сожалеем, что пришлось столкнуться с проблемой. Укажи основную суть, свою роль и роль/роли тех, на кого хочешь пожаловаться.",
            "Другое":"Добрый день! Расскажи цель обращения и назови свою роль — постараемся помочь 🫶"}
        await state.update_data(ticket_type=types[message.text]); await message.answer(prompts[types[message.text]]); return
    d=await state.get_data()
    if not d.get("ticket_type"): return await message.answer("Сначала выбери тип обращения кнопкой выше.")
    await state.update_data(text=(message.text or "").strip())
    await message.answer("Проверь обращение перед отправкой 🫶\n\n"+(message.text or ""),reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Отправить",callback_data="ticket:send")],
        [InlineKeyboardButton(text="✏️ Редактировать",callback_data="ticket:edit")],
        [InlineKeyboardButton(text="❌ Отмена",callback_data="ticket:cancel")]]))
    await state.set_state(SupportStates.preview)

@router.callback_query(F.data=="ticket:edit")
async def ticket_edit(call,state:FSMContext):
    await state.set_state(SupportStates.writing); await call.message.answer("Перепиши обращение целиком."); await call.answer()

@router.callback_query(F.data=="ticket:cancel")
async def ticket_cancel(call,state:FSMContext):
    await state.clear(); await call.message.answer("Обращение отменено.",reply_markup=user_main()); await call.answer()

@router.callback_query(F.data=="ticket:send")
async def ticket_send(call,state:FSMContext):
    d=await state.get_data()
    if await db.is_banned(call.from_user.id): await state.clear(); return await call.answer("Доступ ограничен.",show_alert=True)
    tid=await db.create_ticket(call.from_user.id,d["ticket_type"],d["text"])
    await db.add_ticket_message(tid,call.from_user.id,"user",text=d["text"])
    await state.clear(); await call.message.answer("Благодарю за обращение! Мы передали его администрации. Ожидай ответа 🫶",reply_markup=user_main())
    from handlers.admin import notify_admins_about_ticket
    await notify_admins_about_ticket(call.bot,tid); await call.answer("Отправлено!")
