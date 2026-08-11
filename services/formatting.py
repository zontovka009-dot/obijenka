import json

def application_text(data, app_id=None, status=None):
    head = f"📝 <b>Анкета №{app_id}</b>\n\n" if app_id else "📝 <b>Анкета</b>\n\n"
    text = (
        head +
        f"🎭 <b>Желаемая роль:</b> {data.get('role','—')}\n"
        f"🎂 <b>День рождения:</b> {data.get('birthday','—')}\n"
        f"💬 <b>О себе:</b>\n{data.get('about','—')}"
    )
    if status:
        text += f"\n\n<b>Статус:</b> {status}"
    return text

def json_data(data):
    return json.dumps(data, ensure_ascii=False)
