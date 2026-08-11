from aiogram.fsm.state import State, StatesGroup

class ApplicationStates(StatesGroup):
    consent = State()
    role = State()
    birthday = State()
    about = State()
    photo = State()
    preview = State()
    edit_value = State()
    profile_edit_value = State()
