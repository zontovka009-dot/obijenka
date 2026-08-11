
import json, re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.application import ApplicationStates
from keyboards.user import user_main, back
from keyboards.inline import app_edit, confirm, profile_edit, user_profile_self
from services.formatting import application_text, json_data
import database as db

router=Router()

async def blocked(uid): return await db.is_banned(uid)

def valid_date(v): return bool(re.fullmatch(r"(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])",v))

async def get_profile_data(uid):
    app=await db.get_user_application(uid)
    if not app: return None, {}
    try: data=json.loads(app[2])
    except Exception: data={}
    return app,data

@router.message(F.text=="📝 Отправить анкету")
async def application_start(message:Message,state:FSMContext):
    if await blocked(message.from_user.id): return await message.answer("Доступ к боту ограничен администрацией.")
    app,data=await get_profile_data(message.from_user.id)
    if app:
        status=app[4]
        if status=="pending":
            return await message.answer("Твоя анкета уже находится на рассмотрении 🫶\nВторую создать нельзя — можешь открыть «👤 Мой профиль» и проверить данные.")
        return await message.answer("У тебя уже есть профиль в боте 🫶\nВторая анкета не создаётся. Если хочешь что-то изменить — открой «👤 Мой профиль».",reply_markup=user_main(status=="approved"))
    await state.clear()
    template=await db.get_setting("application_template","")
    photo=await db.get_setting("application_template_photo","")
    intro=template or ("Перед заполнением загляни в ТГК, указанном в профиле бота, и ознакомься со свободными ролями.\n\n"
                       "Дальше попросим желаемую роль, день/месяц рождения и немного о себе.")
    if photo:
        try: await message.answer_photo(photo,caption="Привет! Рады видеть тебя здесь 🫶\n\n"+intro)
        except Exception: await message.answer("Привет! Рады видеть тебя здесь 🫶\n\n"+intro,reply_markup=back())
    else: await message.answer("Привет! Рады видеть тебя здесь 🫶\n\n"+intro,reply_markup=back())
    await message.answer("Ознакомился(ась) со свободными ролями?",reply_markup=__import__("aiogram").types.ReplyKeyboardMarkup(keyboard=[[__import__("aiogram").types.KeyboardButton(text="✅ Я ознакомился(ась)")],[__import__("aiogram").types.KeyboardButton(text="↩️ Назад")]],resize_keyboard=True))
    await state.set_state(ApplicationStates.consent)

@router.message(ApplicationStates.consent)
async def consent(message:Message,state:FSMContext):
    if message.text=="↩️ Назад": await state.clear(); return await message.answer("Вернулись 🫶",reply_markup=user_main())
    if message.text!="✅ Я ознакомился(ась)": return await message.answer("Нажми кнопку «✅ Я ознакомился(ась)», когда посмотришь свободные роли.")
    await message.answer("Отлично! Теперь самое важное 🎭\n\nНапиши желаемую свободную роль.")
    await state.set_state(ApplicationStates.role)

@router.message(ApplicationStates.role)
async def role(message:Message,state:FSMContext):
    if not message.text: return await message.answer("Напиши роль текстом.")
    await state.update_data(role=message.text.strip())
    await message.answer("Отлично! 🎂 Теперь укажи день и месяц рождения в формате <b>ДД/ММ</b>.",parse_mode="HTML")
    await state.set_state(ApplicationStates.birthday)

@router.message(ApplicationStates.birthday)
async def birthday(message:Message,state:FSMContext):
    v=(message.text or "").strip()
    if not valid_date(v): return await message.answer("Нужен формат <b>ДД/ММ</b>, например 17/09.",parse_mode="HTML")
    await state.update_data(birthday=v)
    await message.answer("Теперь немного о себе 💬\n\nЭто необязательно — можешь написать «пропуск».")
    await state.set_state(ApplicationStates.about)

@router.message(ApplicationStates.about)
async def about(message:Message,state:FSMContext):
    v=(message.text or "").strip()
    await state.update_data(about="—" if v.lower()=="пропуск" else v,photo_file_id=None)
    await message.answer("Хочешь добавить одну фотографию? 🖼\nОтправь её или напиши «пропуск».")
    await state.set_state(ApplicationStates.photo)

@router.message(ApplicationStates.photo)
async def photo(message:Message,state:FSMContext):
    if message.photo: await state.update_data(photo_file_id=message.photo[-1].file_id)
    elif (message.text or "").strip().lower() in {"пропуск","нет","не хочу"}: await state.update_data(photo_file_id=None)
    else: return await message.answer("Отправь одну фотографию или напиши «пропуск».")
    data=await state.get_data()
    await message.answer("Проверь анкету перед отправкой 🫶\n\n"+application_text(data),parse_mode="HTML",reply_markup=confirm("app","app:send","app:edit"))
    await state.set_state(ApplicationStates.preview)

@router.callback_query(F.data=="app:edit")
async def app_edit_cb(call:CallbackQuery,state:FSMContext):
    await call.message.edit_reply_markup(reply_markup=app_edit()); await call.answer()

@router.callback_query(F.data.startswith("appedit:"))
async def app_edit_field(call:CallbackQuery,state:FSMContext):
    action=call.data.split(":")[1]
    if action=="done":
        data=await state.get_data()
        await call.message.edit_text("Проверь обновлённый вариант 🫶\n\n"+application_text(data),parse_mode="HTML")
        await call.message.edit_reply_markup(reply_markup=confirm("app","app:send","app:edit"))
        await state.set_state(ApplicationStates.preview); return await call.answer()
    await state.update_data(edit_field=action)
    if action=="photo": prompt="Отправь новую фотографию или напиши «удалить»."
    else: prompt={"role":"Напиши новую роль.","birthday":"Напиши новую дату в формате ДД/ММ.","about":"Напиши новый текст о себе."}[action]
    await call.message.answer(prompt); await state.set_state(ApplicationStates.edit_value); await call.answer()

@router.message(ApplicationStates.edit_value)
async def app_edit_value(message:Message,state:FSMContext):
    d=await state.get_data(); field=d.get("edit_field")
    if field=="photo":
        if message.photo: await state.update_data(photo_file_id=message.photo[-1].file_id)
        elif (message.text or "").lower()=="удалить": await state.update_data(photo_file_id=None)
        else: return await message.answer("Нужна фотография или «удалить».")
    elif field=="birthday":
        if not valid_date((message.text or "").strip()): return await message.answer("Формат: ДД/ММ.")
        await state.update_data(birthday=message.text.strip())
    else: await state.update_data(**{field:(message.text or "").strip()})
    data=await state.get_data()
    await message.answer("Готово 🫶\n\n"+application_text(data),parse_mode="HTML",reply_markup=confirm("app","app:send","app:edit"))
    await state.set_state(ApplicationStates.preview)

@router.callback_query(F.data=="app:send")
async def app_send(call:CallbackQuery,state:FSMContext):
    if await blocked(call.from_user.id): await state.clear(); return await call.answer("Доступ ограничен.",show_alert=True)
    data=await state.get_data(); old=await db.get_user_application(call.from_user.id)
    app_id=await db.create_application(call.from_user.id,json_data(data),data.get("photo_file_id"))
    await state.clear()
    await call.message.answer("Анкета отправлена администрации 🫶\nОжидай решения!",reply_markup=user_main(False))
    from handlers.admin import notify_admins_about_application
    await notify_admins_about_application(call.bot,app_id)
    await call.answer("Отправлено!")

@router.message(F.text=="👤 Мой профиль")
async def profile(message:Message):
    if await blocked(message.from_user.id): return await message.answer("Доступ к боту ограничен администрацией.")
    app,data=await get_profile_data(message.from_user.id)
    if not app: return await message.answer("Профиль пока пуст — сначала заполни анкету 🫶",reply_markup=user_main())
    status={"pending":"🟡 На рассмотрении","approved":"🟢 Участник","rejected":"🔴 Отклонена","blocked":"🚫 Заблокирована"}.get(app[4],app[4])
    await message.answer("👤 <b>Твой профиль</b>\n\n"+application_text(data,app[0],status)+
                         "\n\nЗдесь хранится твоя единственная анкета. Её можно редактировать.",parse_mode="HTML",
                         reply_markup=user_profile_self(app[4]))


@router.callback_query(F.data=="profile:resubmit")
async def profile_resubmit(call):
    app,data=await get_profile_data(call.from_user.id)
    if not app or app[4]!="rejected": return await call.answer("Сейчас повторная отправка недоступна.",show_alert=True)
    await db.update_application_data(app[0],json_data(data),data.get("photo_file_id"),status="pending")
    await call.message.answer("Изменения отправлены администрации 🫶\nОжидай решения!")
    from handlers.admin import notify_admins_about_application
    await notify_admins_about_application(call.bot,app[0])
    await call.answer("Отправлено!")

@router.callback_query(F.data=="profile:edit")
async def profile_edit_start(call,state:FSMContext):
    app,data=await get_profile_data(call.from_user.id)
    if not app: return await call.answer("Профиль пуст.",show_alert=True)
    await state.clear(); await state.update_data(profile_edit=True)
    await call.message.answer("Что хочешь изменить?",reply_markup=profile_edit()); await call.answer()

@router.callback_query(F.data=="profile:back")
async def profile_back(call,state:FSMContext):
    await state.clear(); await call.answer(); await call.message.answer("Профиль оставлен без изменений 🫶")

@router.callback_query(F.data.startswith("profileedit:"))
async def profile_edit_field(call,state:FSMContext):
    action=call.data.split(":")[1]
    if action=="back": await state.clear(); return await call.answer()
    await state.update_data(edit_field=action)
    await call.message.answer({"role":"Напиши новую роль.","birthday":"Напиши новую дату ДД/ММ.","about":"Напиши новый текст о себе.","photo":"Отправь фото или «удалить»."}[action])
    await state.set_state(ApplicationStates.profile_edit_value); await call.answer()

@router.message(ApplicationStates.profile_edit_value)
async def profile_edit_value(message:Message,state:FSMContext):
    app,data=await get_profile_data(message.from_user.id); st=await state.get_data(); field=st.get("edit_field")
    if not app: await state.clear(); return
    if field=="photo":
        if message.photo: data["photo_file_id"]=message.photo[-1].file_id
        elif (message.text or "").lower()=="удалить": data["photo_file_id"]=None
        else: return await message.answer("Отправь фото или «удалить».")
    elif field=="birthday":
        if not valid_date((message.text or "").strip()): return await message.answer("Формат: ДД/ММ.")
        data["birthday"]=message.text.strip()
    else: data[field]=(message.text or "").strip()
    await db.update_application_data(app[0],json_data(data),data.get("photo_file_id"))
    await state.clear()
    await message.answer("Профиль обновлён 🫶",reply_markup=user_main(app[4]=="approved"))

@router.message(F.text=="📨 Мои обращения")
async def my_tickets(message:Message):
    if await blocked(message.from_user.id): return await message.answer("Доступ к боту ограничен администрацией.")
    ts=await db.get_user_tickets(message.from_user.id)
    if not ts: return await message.answer("Пока обращений нет 🫶")
    await message.answer("📨 <b>Твои обращения</b>\n\n"+"\n".join(f"№{t[0]} — {t[1]} — {t[2]}" for t in ts),parse_mode="HTML")
