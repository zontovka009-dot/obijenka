
import json, functools
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import ADMIN_IDS, GROUP_LINK
from keyboards.admin import admin_main
from keyboards.inline import app_actions, claimed_app_actions, app_lists, ticket_lists, ticket_actions, blacklist_actions, admin_message_confirm, admin_reply_confirm, user_profile_admin
from states.admin import AdminStates
from states.support import SupportStates
from services.formatting import application_text
from services.cats import random_cat
import database as db

router=Router()

def admin_only(handler):
    @functools.wraps(handler)
    async def wrapper(event,*args,**kwargs):
        if not event.from_user or event.from_user.id not in ADMIN_IDS:
            try: await event.answer("Нет доступа.",show_alert=True)
            except Exception: pass
            return
        return await handler(event,*args,**kwargs)
    return wrapper

def admin_user_name(row):
    return f"@{row[1]}" if row and row[1] else (row[2] if row else "без username")

async def edit_admin_app_message(bot, admin_id, message_id, text, photo=False, kb=None):
    try:
        if photo:
            await bot.edit_message_caption(chat_id=admin_id,message_id=message_id,caption=text,parse_mode="HTML",reply_markup=kb)
        else:
            await bot.edit_message_text(chat_id=admin_id,message_id=message_id,text=text,parse_mode="HTML",reply_markup=kb)
    except Exception:
        try: await bot.edit_message_reply_markup(chat_id=admin_id,message_id=message_id,reply_markup=kb)
        except Exception: pass

async def sync_app_messages(bot, app_id, claimed_by=None, final_status=None):
    app=await db.get_application(app_id)
    if not app: return
    data=json.loads(app[2]); user=await db.get_user(app[1])
    status = final_status or ("👁 В работе у администрации" if claimed_by else "🟡 На рассмотрении")
    text=f"📝 <b>Анкета №{app_id}</b>\n\n👤 {admin_user_name(user)}\n🆔 <code>{app[1]}</code>\n\n"+application_text(data,app_id,status)
    for aid,mid in await db.app_messages(app_id):
        enabled = claimed_by is None
        if final_status:
            kb=None
        elif claimed_by == aid:
            kb=claimed_app_actions(app_id)
        elif claimed_by:
            kb=app_actions(app_id,False)
        else:
            kb=app_actions(app_id,True)
        await edit_admin_app_message(bot,aid,mid,text,bool(app[3]),kb)

async def notify_admins_about_application(bot,app_id):
    app=await db.get_application(app_id)
    if not app:return
    data=json.loads(app[2]); user=await db.get_user(app[1])
    text=f"📝 <b>Новая анкета №{app_id}</b>\n\n👤 {admin_user_name(user)}\n🆔 <code>{app[1]}</code>\n\n"+application_text(data,app_id,"🟡 На рассмотрении")
    for aid in ADMIN_IDS:
        try:
            if app[3]:
                m=await bot.send_photo(aid,app[3],caption=text,parse_mode="HTML",reply_markup=app_actions(app_id,True))
            else:
                m=await bot.send_message(aid,text,parse_mode="HTML",reply_markup=app_actions(app_id,True))
            await db.save_app_message(app_id,aid,m.message_id)
        except Exception: pass

async def notify_admins_about_ticket(bot,ticket_id):
    t=await db.get_ticket(ticket_id)
    if not t:return
    u=await db.get_user(t[1])
    text=f"🆘 <b>Новое обращение №{ticket_id}</b>\n\nТип: {t[2]}\n👤 {admin_user_name(u)}\n🆔 <code>{t[1]}</code>\n\n{t[3]}"
    for aid in ADMIN_IDS:
        try: await bot.send_message(aid,text,parse_mode="HTML",reply_markup=ticket_actions(ticket_id))
        except Exception: pass

@router.message(F.text=="📋 Посмотреть заявки")
@admin_only
async def applications(message):
    await message.answer("Что вас интересует? 🫶",reply_markup=app_lists())

@router.callback_query(F.data=="nav:admin")
@admin_only
async def nav_admin(call):
    await call.message.answer("Панель управления 👑",reply_markup=admin_main()); await call.answer()

@router.callback_query(F.data.startswith("apps:"))
@admin_only
async def app_list(call):
    mode=call.data.split(":")[1]
    rows=(await db.list_applications("pending") if mode=="pending" else
          await db.list_applications("approved")+await db.list_applications("rejected")+await db.list_applications("blocked"))
    if not rows:return await call.answer("Здесь пока пусто.",show_alert=True)
    buttons=[]
    for r in rows[:50]:
        claimed=f" 👁 @{r[6]}" if False else (" 👁" if r[6] else "")
        buttons.append([InlineKeyboardButton(text=f"№{r[0]} — {admin_user_name((r[4],r[5]))} — {r[2]}{claimed}",callback_data=f"viewapp:{r[0]}")])
    buttons.append([InlineKeyboardButton(text="↩️ Назад",callback_data="nav:admin")])
    await call.message.edit_text("📋 <b>Заявки</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@router.callback_query(F.data.startswith("viewapp:"))
@admin_only
async def view_app(call):
    app=await db.get_application(int(call.data.split(":")[1]))
    if not app:return await call.answer("Не найдено.",show_alert=True)
    data=json.loads(app[2]); claimed=app[9] if len(app)>9 else None
    text=application_text(data,app[0],app[4])
    if app[3]: await call.message.answer_photo(app[3],caption=text,parse_mode="HTML",reply_markup=claimed_app_actions(app[0]) if claimed==call.from_user.id else (app_actions(app[0],False) if claimed else app_actions(app[0],True)))
    else: await call.message.answer(text,parse_mode="HTML",reply_markup=claimed_app_actions(app[0]) if claimed==call.from_user.id else (app_actions(app[0],False) if claimed else app_actions(app[0],True)))
    await call.answer()

@router.callback_query(F.data.startswith("app:claim:"))
@admin_only
async def claim(call):
    aid=int(call.data.split(":")[2])
    ok=await db.claim_application(aid,call.from_user.id)
    if not ok:return await call.answer("Эту заявку уже взял другой администратор.",show_alert=True)
    await sync_app_messages(call.bot,aid,call.from_user.id)
    await call.answer("Заявка закреплена за тобой 🫡")

@router.callback_query(F.data.startswith("app:release:"))
@admin_only
async def release(call):
    aid=int(call.data.split(":")[2]); app=await db.get_application(aid)
    if not app or app[4]!="pending":return await call.answer("Заявка уже обработана.",show_alert=True)
    if app[9]!=call.from_user.id:return await call.answer("Эта заявка закреплена за другим админом.",show_alert=True)
    async with __import__("aiosqlite").connect(db.DB_PATH) as conn:
        await conn.execute("UPDATE applications SET claimed_by=NULL,claimed_at=NULL WHERE id=?",(aid,)); await conn.commit()
    await sync_app_messages(call.bot,aid,None); await call.answer("Заявка снова в очереди.")

async def require_claim(call,aid):
    app=await db.get_application(aid)
    if not app or app[4]!="pending":
        await call.answer("Заявка уже обработана.",show_alert=True); return None
    if app[9] not in (None,call.from_user.id):
        await call.answer("Эту заявку уже обрабатывает другой администратор.",show_alert=True); return None
    if app[10] is None:
        if not await db.claim_application(aid,call.from_user.id):
            await call.answer("Её уже взял другой администратор.",show_alert=True); return None
    return app

@router.callback_query(F.data.startswith("app:approve:"))
@admin_only
async def approve(call):
    aid=int(call.data.split(":")[2]); app=await require_claim(call,aid)
    if not app:return
    await db.update_application(aid,"approved",call.from_user.id)
    link=await db.get_setting("group_link",GROUP_LINK)
    msg="🎉 Ура! Твою анкету одобрили!\n\nДобро пожаловать во флуд 🫶"
    if link: msg+=f"\n\nЗаходи к нам:\n{link}"
    try: await call.bot.send_message(app[1],msg)
    except Exception: pass
    await sync_app_messages(call.bot,aid,call.from_user.id,"🟢 Одобрена")
    await call.message.answer(f"Анкета №{aid} одобрена ✅"); await call.answer("Готово!")

@router.callback_query(F.data.startswith("app:reject:"))
@admin_only
async def reject_start(call,state):
    aid=int(call.data.split(":")[2]); app=await require_claim(call,aid)
    if not app:return
    await state.update_data(app_id=aid,admin_id=call.from_user.id)
    await state.set_state(AdminStates.reject_reason)
    await call.message.answer("Напиши причину отклонения. Пользователь её увидит."); await call.answer()

@router.message(AdminStates.reject_reason)
@admin_only
async def reject_reason(message,state):
    d=await state.get_data()
    if not d.get("app_id"):return
    await state.update_data(reason=message.text or "Без причины")
    await message.answer("Причина:\n\n"+(message.text or "Без причины")+"\n\nОтправить?",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Отправить",callback_data=f"appreject:send:{d['app_id']}")],
        [InlineKeyboardButton(text="✏️ Изменить",callback_data=f"appreject:edit:{d['app_id']}")],
        [InlineKeyboardButton(text="❌ Отмена",callback_data="appreject:cancel")]]))

@router.callback_query(F.data.startswith("appreject:send:"))
@admin_only
async def reject_send(call,state):
    aid=int(call.data.split(":")[2]); d=await state.get_data(); app=await require_claim(call,aid)
    if not app:return
    await db.update_application(aid,"rejected",call.from_user.id,d.get("reason","—"))
    try: await call.bot.send_message(app[1],f"Анкету пока не удалось одобрить 🫶\n\nПричина:\n{d.get('reason','—')}\n\nТы можешь отредактировать единственный профиль и отправить изменения повторно.")
    except Exception: pass
    await state.clear(); await sync_app_messages(call.bot,aid,call.from_user.id,"🔴 Отклонена"); await call.answer("Отклонено!")

@router.callback_query(F.data.startswith("appreject:edit:"))
@admin_only
async def reject_edit(call,state):
    await call.message.answer("Напиши новую причину."); await call.answer()

@router.callback_query(F.data=="appreject:cancel")
@admin_only
async def reject_cancel(call,state):
    await state.clear(); await call.answer("Отмена")

@router.callback_query(F.data.startswith("app:ban:"))
@admin_only
async def app_ban_start(call,state):
    aid=int(call.data.split(":")[2]); app=await require_claim(call,aid)
    if not app:return
    await state.update_data(app_id=aid,ban_target=app[1]); await state.set_state(AdminStates.ban_reason)
    await call.message.answer("Напиши причину блокировки."); await call.answer()

@router.message(AdminStates.ban_reason)
@admin_only
async def app_ban_reason(message,state):
    d=await state.get_data(); uid=d["ban_target"]; reason=message.text or "Без причины"
    await db.ban_user(uid,reason,message.from_user.id)
    if d.get("app_id"):
        await db.update_application(d["app_id"],"blocked",message.from_user.id,reason)
        await sync_app_messages(message.bot,d["app_id"],message.from_user.id,"🚫 Заблокирован")
    if d.get("ticket_id"):
        await db.close_ticket(d["ticket_id"],"blocked",message.from_user.id)
    try: await message.bot.send_message(uid,"🚫 Доступ к боту ограничен администрацией.\n\nПричина:\n"+reason)
    except Exception:pass
    await state.clear(); await message.answer("Пользователь заблокирован 🚫",reply_markup=admin_main())

@router.message(F.text=="🆘 Посмотреть обращения")
@admin_only
async def tickets(message): await message.answer("Что вас интересует? 🫶",reply_markup=ticket_lists())

@router.callback_query(F.data.startswith("tickets:"))
@admin_only
async def ticket_list(call):
    mode=call.data.split(":")[1]
    rows=await db.list_tickets("pending") if mode=="pending" else await db.list_tickets("answered")+await db.list_tickets("rejected")+await db.list_tickets("blocked")
    if not rows:return await call.answer("Здесь пока пусто.",show_alert=True)
    buttons=[[InlineKeyboardButton(text=f"№{r[0]} — {r[2]} — {admin_user_name((r[5],r[6]))}",callback_data=f"viewticket:{r[0]}")] for r in rows[:50]]
    buttons.append([InlineKeyboardButton(text="↩️ Назад",callback_data="nav:admin")])
    await call.message.edit_text("🆘 <b>Обращения</b>",parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await call.answer()

@router.callback_query(F.data.startswith("viewticket:"))
@admin_only
async def view_ticket(call):
    tid=int(call.data.split(":")[1]); t=await db.get_ticket(tid)
    if not t:return await call.answer("Не найдено.",show_alert=True)
    msgs=await db.get_ticket_messages(tid)
    text=f"🆘 <b>Обращение №{tid}</b>\n\nТип: {t[2]}\nID: <code>{t[1]}</code>\nСтатус: {t[4]}\n\n📜 <b>История:</b>\n"
    text+="\n".join(("👤 Пользователь" if m[1]=="user" else "👑 Администратор")+":\n"+(m[2] or "📷 Фото") for m in msgs)
    await call.message.answer(text,parse_mode="HTML",reply_markup=ticket_actions(tid) if t[4]=="pending" else None); await call.answer()

@router.callback_query(F.data.startswith("ticket:reply:"))
@admin_only
async def ticket_reply_start(call,state):
    tid=int(call.data.split(":")[2]); t=await db.get_ticket(tid)
    if not t or t[4]!="pending":return await call.answer("Уже обработано.",show_alert=True)
    await state.update_data(ticket_id=tid); await state.set_state(SupportStates.admin_reply)
    await call.message.answer("Напиши ответ. Можно текст или фото с подписью."); await call.answer()

@router.callback_query(F.data.startswith("ticket:reject:"))
@admin_only
async def ticket_reject_start(call,state):
    tid=int(call.data.split(":")[2]); t=await db.get_ticket(tid)
    if not t or t[4]!="pending":return await call.answer("Уже обработано.",show_alert=True)
    await state.update_data(ticket_id=tid); await state.set_state(SupportStates.admin_reject)
    await call.message.answer("Напиши причину отклонения."); await call.answer()

@router.callback_query(F.data.startswith("ticket:ban:"))
@admin_only
async def ticket_ban_start(call,state):
    tid=int(call.data.split(":")[2]); t=await db.get_ticket(tid)
    if not t or t[4]!="pending":return await call.answer("Уже обработано.",show_alert=True)
    await state.update_data(ticket_id=tid,ban_target=t[1]); await state.set_state(AdminStates.ban_reason)
    await call.message.answer("Напиши причину блокировки."); await call.answer()

@router.message(SupportStates.admin_reply)
@admin_only
async def ticket_reply_content(message,state):
    if not message.text and not message.photo:return await message.answer("Нужен текст или фото.")
    await state.update_data(reply_text=message.caption if message.photo else message.text,reply_photo=message.photo[-1].file_id if message.photo else None)
    d=await state.get_data(); preview=d.get("reply_text") or "📷 Фото без подписи"
    await message.answer("Проверь ответ:\n\n"+preview,reply_markup=admin_reply_confirm(d["ticket_id"]))
    if d.get("reply_photo"): await message.answer_photo(d["reply_photo"],caption=d.get("reply_text"))
    await state.set_state(SupportStates.admin_reply_preview)

@router.callback_query(F.data.startswith("treply:send:"))
@admin_only
async def ticket_reply_send(call,state):
    tid=int(call.data.split(":")[2]); d=await state.get_data(); t=await db.get_ticket(tid)
    if not t or t[4]!="pending":await state.clear(); return await call.answer("Уже обработано.",show_alert=True)
    try:
        if d.get("reply_photo"): await call.bot.send_photo(t[1],d["reply_photo"],caption="💬 <b>Сообщение от администрации</b>\n\n"+(d.get("reply_text") or ""),parse_mode="HTML")
        else: await call.bot.send_message(t[1],"💬 <b>Сообщение от администрации</b>\n\n"+(d.get("reply_text") or ""),parse_mode="HTML")
    except Exception: pass
    await db.add_ticket_message(tid,call.from_user.id,"admin",d.get("reply_text"),d.get("reply_photo")); await db.close_ticket(tid,"answered",call.from_user.id)
    await state.clear(); await call.message.answer("Ответ отправлен пользователю 💌"); await call.answer("Готово!")

@router.callback_query(F.data.startswith("treply:edit:"))
@admin_only
async def ticket_reply_edit(call,state): await state.set_state(SupportStates.admin_reply); await call.message.answer("Отправь новый вариант."); await call.answer()

@router.callback_query(F.data.startswith("treply:cancel:"))
@admin_only
async def ticket_reply_cancel(call,state): await state.clear(); await call.answer("Отмена")

@router.message(SupportStates.admin_reject)
@admin_only
async def ticket_reject_content(message,state):
    d=await state.get_data(); await state.update_data(reject_reason=message.text or "Без причины")
    await message.answer("Причина:\n\n"+(message.text or "Без причины")+"\n\nПодтвердить?",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Отправить",callback_data=f"treject:send:{d['ticket_id']}")],
        [InlineKeyboardButton(text="✏️ Изменить",callback_data=f"treject:edit:{d['ticket_id']}")],
        [InlineKeyboardButton(text="❌ Отмена",callback_data=f"treject:cancel:{d['ticket_id']}")]]))
@router.callback_query(F.data.startswith("treject:send:"))
@admin_only
async def ticket_reject_send(call,state):
    tid=int(call.data.split(":")[2]); d=await state.get_data(); t=await db.get_ticket(tid)
    if not t or t[4]!="pending":return await call.answer("Уже обработано.",show_alert=True)
    await db.close_ticket(tid,"rejected",call.from_user.id)
    try: await call.bot.send_message(t[1],"Обращение закрыто администрацией.\n\nПричина:\n"+d.get("reject_reason","—"))
    except Exception:pass
    await state.clear(); await call.message.answer("Обращение отклонено ❌"); await call.answer()
@router.callback_query(F.data.startswith("treject:edit:"))
@admin_only
async def ticket_reject_edit(call,state): await call.message.answer("Напиши новую причину."); await call.answer()
@router.callback_query(F.data.startswith("treject:cancel:"))
@admin_only
async def ticket_reject_cancel(call,state): await state.clear(); await call.answer("Отмена")

@router.callback_query(F.data.startswith("ticket:profile:"))
@admin_only
async def ticket_profile(call):
    t=await db.get_ticket(int(call.data.split(":")[2])); await send_user_profile(call,t[1]); await call.answer()

@router.message(F.text=="🚫 Чёрный список")
@admin_only
async def blacklist(message):
    rows=await db.get_blacklist()
    if not rows:return await message.answer("Чёрный список пуст 🫶")
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🚫 {admin_user_name((r[4],r[5]))}",callback_data=f"black:{r[0]}")] for r in rows]+[[InlineKeyboardButton(text="↩️ Назад",callback_data="nav:admin")]])
    await message.answer("🚫 <b>Чёрный список</b>",parse_mode="HTML",reply_markup=kb)

@router.callback_query(F.data=="black:list")
@admin_only
async def black_list(call): await call.message.answer("Открой чёрный список из панели.",reply_markup=admin_main()); await call.answer()

@router.callback_query(F.data.startswith("black:"))
@admin_only
async def black_view(call):
    uid=int(call.data.split(":")[1]); row=next((r for r in await db.get_blacklist() if r[0]==uid),None)
    if not row:return await call.answer("Уже разблокирован.",show_alert=True)
    await call.message.answer(f"🚫 <b>Пользователь</b>\n\nID: <code>{uid}</code>\nПричина: {row[1]}\nЗаблокировал: <code>{row[2]}</code>",parse_mode="HTML",reply_markup=blacklist_actions(uid)); await call.answer()

@router.callback_query(F.data.startswith("unban:"))
@admin_only
async def unban(call):
    uid=int(call.data.split(":")[1]); await db.unban_user(uid); await call.message.answer("Пользователь разблокирован 🔓"); await call.answer()

async def send_user_profile(event,uid):
    u=await db.get_user(uid); app=await db.get_user_application(uid); ts=await db.get_user_tickets(uid)
    data=json.loads(app[2]) if app else {}
    status=app[4] if app else "нет анкеты"
    text=f"👤 <b>Профиль пользователя</b>\n\nИмя: {u[2] if u else '—'}\nUsername: @{u[1] if u and u[1] else 'нет'}\nID: <code>{uid}</code>\nСтатус: {status}\n\n"
    text+=application_text(data,app[0],status) if app else "Анкета ещё не заполнена."
    text+=f"\n\n🆘 Обращений: {len(ts)}"
    await event.message.answer(text,parse_mode="HTML",reply_markup=user_profile_admin(uid))

@router.message(F.text=="👥 Пользователи")
@admin_only
async def users(message): await message.answer("👥 Выбери пользователя:",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"@{r[1]}" if r[1] else (r[2] or str(r[0])),callback_data=f"user:view:{r[0]}")] for r in (await db.list_users())[:50]]))

@router.callback_query(F.data=="users:list")
@admin_only
async def users_list(call): await users(call.message); await call.answer()

@router.callback_query(F.data.startswith("user:view:"))
@admin_only
async def user_view(call): await send_user_profile(call,int(call.data.split(":")[2])); await call.answer()

@router.callback_query(F.data.startswith("user:app:"))
@admin_only
async def user_app(call):
    uid=int(call.data.split(":")[2]); app=await db.get_user_application(uid)
    if not app:return await call.answer("Анкеты нет.",show_alert=True)
    data=json.loads(app[2]); await call.message.answer(application_text(data,app[0],app[4]),parse_mode="HTML"); await call.answer()

@router.callback_query(F.data.startswith("user:tickets:"))
@admin_only
async def user_tickets(call):
    uid=int(call.data.split(":")[2]); ts=await db.get_user_tickets(uid)
    text="🆘 <b>Обращения пользователя</b>\n\n"+("\n".join(f"№{t[0]} — {t[1]} — {t[2]}" for t in ts) if ts else "Нет обращений.")
    await call.message.answer(text,parse_mode="HTML"); await call.answer()

@router.callback_query(F.data.startswith("user:message:"))
@admin_only
async def user_message_start(call,state):
    parts=call.data.split(":")
    uid=None
    if len(parts)==3 and parts[1]=="message": uid=int(parts[2])
    elif len(parts)==4 and parts[2]=="app":
        app=await db.get_application(int(parts[3])); uid=app[1] if app else None
    if not uid:return await call.answer("Пользователь не найден.",show_alert=True)
    await state.update_data(message_target=uid); await state.set_state(AdminStates.user_message)
    await call.message.answer("Напиши сообщение пользователю. Можно текст или фото с подписью."); await call.answer()

@router.message(AdminStates.user_message)
@admin_only
async def user_message_content(message,state):
    if not message.text and not message.photo:return await message.answer("Нужен текст или фото.")
    await state.update_data(msg_text=message.caption if message.photo else message.text,msg_photo=message.photo[-1].file_id if message.photo else None)
    d=await state.get_data(); uid=d["message_target"]
    await message.answer("Проверь сообщение перед отправкой:\n\n"+(d.get("msg_text") or "📷 Фото без подписи"),reply_markup=admin_message_confirm(uid))
    if d.get("msg_photo"):await message.answer_photo(d["msg_photo"],caption=d.get("msg_text"))
    await state.set_state(AdminStates.user_message_preview)

@router.callback_query(F.data.startswith("umsg:send:"))
@admin_only
async def user_message_send(call,state):
    uid=int(call.data.split(":")[2]); d=await state.get_data()
    try:
        if d.get("msg_photo"):await call.bot.send_photo(uid,d["msg_photo"],caption="💌 <b>Сообщение от администрации</b>\n\n"+(d.get("msg_text") or ""),parse_mode="HTML")
        else:await call.bot.send_message(uid,"💌 <b>Сообщение от администрации</b>\n\n"+(d.get("msg_text") or ""),parse_mode="HTML")
    except Exception:return await call.answer("Не удалось доставить сообщение.",show_alert=True)
    await state.clear(); await call.message.answer("Сообщение отправлено 💌"); await call.answer()

@router.callback_query(F.data.startswith("umsg:edit:"))
@admin_only
async def user_message_edit(call,state): await state.set_state(AdminStates.user_message); await call.message.answer("Отправь новый вариант."); await call.answer()
@router.callback_query(F.data.startswith("umsg:cancel:"))
@admin_only
async def user_message_cancel(call,state): await state.clear(); await call.answer("Отмена")

@router.callback_query(F.data.startswith("user:ban:"))
@admin_only
async def user_ban_start(call,state):
    uid=int(call.data.split(":")[2]); await state.update_data(ban_target=uid); await state.set_state(AdminStates.ban_reason); await call.message.answer("Напиши причину блокировки."); await call.answer()

@router.message(F.text=="👑 Список админов")
@admin_only
async def admins(message):
    lines=["👑 <b>Администраторы</b>\n"]
    for uid in sorted(ADMIN_IDS):
        u=await db.get_user(uid); lines.append(f"• @{u[1] if u and u[1] else 'нет username'} — <code>{uid}</code>")
    await message.answer("\n".join(lines),parse_mode="HTML")

@router.message(F.text=="📝 Анкета заявок")
@admin_only
async def template_menu(message):
    cur=await db.get_setting("application_template",""); photo=await db.get_setting("application_template_photo","")
    text="📝 <b>Настройки анкеты</b>\n\n"+(cur or "Базовый текст используется автоматически.")+"\n\nКартинка: "+("есть 🖼" if photo else "нет")
    await message.answer(text,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст",callback_data="settings:template")],
        [InlineKeyboardButton(text="🖼 Изменить картинку",callback_data="settings:template_photo")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку на группу",callback_data="settings:link")],
        [InlineKeyboardButton(text="👁 Предпросмотр",callback_data="settings:preview")],
        [InlineKeyboardButton(text="↩️ Назад",callback_data="nav:admin")]]))

@router.callback_query(F.data=="settings:template")
@admin_only
async def template_edit(call,state): await state.set_state(AdminStates.edit_template); await state.update_data(editing_template_photo=False); await call.message.answer("Пришли новый текст шаблона."); await call.answer()
@router.callback_query(F.data=="settings:template_photo")
@admin_only
async def template_photo_edit(call,state): await state.set_state(AdminStates.edit_template); await state.update_data(editing_template_photo=True); await call.message.answer("Пришли одну фотографию или напиши «удалить»."); await call.answer()
@router.message(AdminStates.edit_template)
@admin_only
async def template_save(message,state):
    d=await state.get_data()
    if d.get("editing_template_photo"):
        if message.photo: await db.set_setting("application_template_photo",message.photo[-1].file_id)
        elif (message.text or "").lower()=="удалить": await db.set_setting("application_template_photo","")
        else:return await message.answer("Нужна фотография или «удалить».")
    else: await db.set_setting("application_template",message.text or "")
    await state.clear(); await message.answer("Сохранено 🫶",reply_markup=admin_main())
@router.callback_query(F.data=="settings:link")
@admin_only
async def link_edit(call,state): await state.set_state(AdminStates.edit_group_link); await call.message.answer("Пришли новую ссылку или «удалить»."); await call.answer()
@router.message(AdminStates.edit_group_link)
@admin_only
async def link_save(message,state):
    await db.set_setting("group_link","" if (message.text or "").lower()=="удалить" else (message.text or "").strip()); await state.clear(); await message.answer("Ссылка сохранена 🔗",reply_markup=admin_main())
@router.callback_query(F.data=="settings:preview")
@admin_only
async def template_preview(call):
    t=await db.get_setting("application_template",""); p=await db.get_setting("application_template_photo","")
    text=t or "Базово: ознакомление со свободными ролями → роль → ДД/ММ → о себе → фото (необязательно)."
    if p:
        try: await call.message.answer_photo(p,caption=text)
        except Exception: await call.message.answer(text)
    else: await call.message.answer(text)
    await call.answer()

@router.message(F.text=="🐈 Если рвёт крышу")
@admin_only
async def cat(message):
    p=random_cat()
    if p: await message.answer_photo(FSInputFile(str(p)),caption="Держи. Кажется, тебе это сейчас необходимо. 🐈")
    else: await message.answer("Котики не завезлись 😭")

@router.callback_query(F.data=="noop")
@admin_only
async def noop(call): await call.answer("Эта заявка уже занята другим администратором.",show_alert=True)
