
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re

# Загружаем переменные окружения
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)

# Открываем таблицу по ссылке и лист с FAQ
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1Ov__Oej19B_a1EKc18pg3qYylfxRwu0ITFrkDpXg53Y")
faq_sheet = sheet.worksheet("FAQ")

app = FastAPI()

# Синонимы вопросов
FAQ_SYNONYMS = {
    "стоимость курса": ["стоимость курса", "цена курса", "цена", "оплата", "оплата обучения", "сколько стоит", "стоимость занятий"],
    "расписание": ["расписание", "время занятий", "когда занятия", "график", "дни занятий", "во сколько уроки"],
    "сертификат": ["сертификат", "документ", "бумага", "диплом", "удостоверение"]
}

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

        # Поиск по синонимам
        for keyword, phrases in FAQ_SYNONYMS.items():
            for phrase in phrases:
                if normalize(phrase) in message_clean:
                    for row in faq_data:
                        if normalize(row.get("Вопрос", "")) == normalize(keyword):
                            answer = row.get("Ответ", "Ответ пока не задан.")
                            print(f"✅ Найден по синониму '{phrase}': {answer}")
                            return PlainTextResponse(answer)

        # Поиск по точному вхождению
        for row in faq_data:
            question = row.get("Вопрос", "").strip().lower()
            answer = row.get("Ответ", "").strip()
            if question and question in message_clean:
                print(f"✅ Ответ из таблицы найден: {answer}")
                return PlainTextResponse(answer or "Ответ пока не задан.")

        # Если не найдено — ChatGPT
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
