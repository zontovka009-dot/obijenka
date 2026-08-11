from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def app_actions(app_id, enabled=True):
    if not enabled:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👁 Уже просмотрена", callback_data="noop")]])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 Взять в работу", callback_data=f"app:claim:{app_id}")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data=f"app:profile:{app_id}")],
    ])

def claimed_app_actions(app_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"app:approve:{app_id}"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"app:reject:{app_id}")],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"app:ban:{app_id}")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data=f"app:profile:{app_id}"), InlineKeyboardButton(text="💬 Написать", callback_data=f"user:message:app:{app_id}")],
        [InlineKeyboardButton(text="↩️ Вернуть в очередь", callback_data=f"app:release:{app_id}")],
    ])

def app_lists():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟡 Активные заявки",callback_data="apps:pending")],[InlineKeyboardButton(text="🟢 Проверенные",callback_data="apps:processed")],[InlineKeyboardButton(text="↩️ Назад",callback_data="nav:admin")]])

def ticket_lists():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟡 Активные обращения",callback_data="tickets:pending")],[InlineKeyboardButton(text="🟢 Обработанные",callback_data="tickets:processed")],[InlineKeyboardButton(text="↩️ Назад",callback_data="nav:admin")]])

def ticket_actions(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Ответить",callback_data=f"ticket:reply:{ticket_id}")],[InlineKeyboardButton(text="❌ Отклонить",callback_data=f"ticket:reject:{ticket_id}"),InlineKeyboardButton(text="🚫 Заблокировать",callback_data=f"ticket:ban:{ticket_id}")],[InlineKeyboardButton(text="👤 Профиль",callback_data=f"ticket:profile:{ticket_id}")]])

def confirm(prefix, yes_data, edit_data):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 Отправить",callback_data=yes_data)],[InlineKeyboardButton(text="✏️ Редактировать",callback_data=edit_data)],[InlineKeyboardButton(text="❌ Отмена",callback_data=f"{prefix}:cancel")]])

def app_edit():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎭 Роль",callback_data="appedit:role"),InlineKeyboardButton(text="🎂 Дата",callback_data="appedit:birthday")],[InlineKeyboardButton(text="💬 О себе",callback_data="appedit:about"),InlineKeyboardButton(text="📷 Фото",callback_data="appedit:photo")],[InlineKeyboardButton(text="✅ Готово",callback_data="appedit:done")]])

def user_profile_self(status="pending"):
    rows=[[InlineKeyboardButton(text="✏️ Редактировать",callback_data="profile:edit")]]
    if status=="rejected": rows.append([InlineKeyboardButton(text="📨 Отправить изменения",callback_data="profile:resubmit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def profile_edit():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎭 Роль",callback_data="appedit:role"),InlineKeyboardButton(text="🎂 Дата",callback_data="appedit:birthday")],[InlineKeyboardButton(text="💬 О себе",callback_data="appedit:about"),InlineKeyboardButton(text="📷 Фото",callback_data="appedit:photo")],[InlineKeyboardButton(text="✅ Готово",callback_data="appedit:done")]])

def user_profile_admin(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Написать",callback_data=f"user:message:{user_id}"),InlineKeyboardButton(text="🚫 Заблокировать",callback_data=f"user:ban:{user_id}")],[InlineKeyboardButton(text="📋 Анкета",callback_data=f"user:app:{user_id}"),InlineKeyboardButton(text="🆘 Обращения",callback_data=f"user:tickets:{user_id}")],[InlineKeyboardButton(text="↩️ Назад",callback_data="users:list")]])

def blacklist_actions(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔓 Разблокировать",callback_data=f"unban:{user_id}")],[InlineKeyboardButton(text="↩️ Назад",callback_data="black:list")]])

def admin_message_confirm(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 Отправить",callback_data=f"umsg:send:{user_id}")],[InlineKeyboardButton(text="✏️ Изменить",callback_data=f"umsg:edit:{user_id}")],[InlineKeyboardButton(text="❌ Отмена",callback_data=f"umsg:cancel:{user_id}")]])

def admin_reply_confirm(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 Отправить",callback_data=f"treply:send:{ticket_id}")],[InlineKeyboardButton(text="✏️ Редактировать",callback_data=f"treply:edit:{ticket_id}")],[InlineKeyboardButton(text="❌ Отмена",callback_data=f"treply:cancel:{ticket_id}")]])
