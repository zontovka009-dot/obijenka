from aiogram.fsm.state import State, StatesGroup

class SupportStates(StatesGroup):
    writing = State()
    preview = State()
    edit = State()
    admin_reply = State()
    admin_reply_preview = State()
    admin_reject = State()
    admin_ban = State()
