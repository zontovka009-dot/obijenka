from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def user_main(member=False):
    rows=[]
    if not member:
        rows.append([KeyboardButton(text="📝 Отправить анкету")])
    rows.append([KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🆘 Поддержка")])
    rows.append([KeyboardButton(text="📨 Мои обращения")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def back():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="↩️ Назад")]], resize_keyboard=True)
