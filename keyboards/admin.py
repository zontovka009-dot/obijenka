from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_main():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Посмотреть заявки"), KeyboardButton(text="🆘 Посмотреть обращения")],
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="🚫 Чёрный список")],
        [KeyboardButton(text="👑 Список админов"), KeyboardButton(text="📝 Анкета заявок")],
        [KeyboardButton(text="🐈 Если рвёт крышу")],
    ], resize_keyboard=True)

def back():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="↩️ Назад")]], resize_keyboard=True)
