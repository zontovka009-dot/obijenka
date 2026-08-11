from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    edit_template = State()
    edit_group_link = State()
    cat_mode = State()
    reject_reason = State()
    ban_reason = State()
    user_message = State()
    user_message_preview = State()
