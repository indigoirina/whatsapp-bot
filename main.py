from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# Загрузка переменных окружения
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1Ov__Oej19B_a1EKc18pg3qYylfxRwu0ITFrkDpXg53Y")
faq_sheet = sheet.worksheet("FAQ")

app = FastAPI()

# Очистка текста от знаков и регистра
def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

@app.get("/")
def root():
    return {"status": "Bot is running ✅"}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    message = form_data.get("Body", "").strip()
    sender = form_data.get("From", "")

    print(f"📩 Получено сообщение от {sender}: {message}")
    if not message:
        return PlainTextResponse("Нет текста", status_code=400)

    try:
        message_clean = normalize(message)
        faq_data = faq_sheet.get_all_records()

        # Проход по строкам таблицы
        for row in faq_data:
            question = row.get("Вопрос", "").strip()
            synonyms = question.lower().split(",") if question else []
            group = row.get("Группа", "").strip()

            for synonym in synonyms:
                if normalize(synonym) in message_clean and group:
                    # Все ответы из этой группы
                    group_answers = [
                        r["Ответ"].strip()
                        for r in faq_data
                        if r.get("Группа", "").strip() == group and r.get("Ответ", "").strip()
                    ]
                    if group_answers:
                        full_reply = "\n".join(group_answers)
                        print(f"✅ Ответы по группе '{group}': {full_reply}")
                        return PlainTextResponse(full_reply)

        # Если ничего не найдено — GPT
        print("🤖 Ответа в таблице нет, обращаемся к ChatGPT...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты — вежливый и профессиональный помощник от имени образовательного центра. "
                        "Твоя задача — грамотно, дружелюбно и понятно отвечать клиентам в WhatsApp. "
                        "Рассказывай про курсы, расписание, цены, формат обучения, документы и сертификаты. "
                        "Если что-то непонятно — переспрашивай. Будь вежливым, как живой человек, а не робот."
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        reply = response.choices[0].message.content.strip()
        print(f"🤖 Ответ от ChatGPT: {reply}")
        return PlainTextResponse(reply)

    except Exception as e:
        print("❌ Ошибка:", str(e))
        return PlainTextResponse("Ошибка сервера", status_code=500)

