
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.rest import Client as TwilioClient

# Загрузка .env
load_dotenv()

# Переменные окружения
api_key = os.getenv("OPENAI_API_KEY")
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Клиенты
gpt = OpenAI(api_key=api_key)
twilio = TwilioClient(twilio_sid, twilio_token)

# Подключение к Google Таблице
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1Ov__Oej19B_a1EKc18pg3qYylfxRwu0ITFrkDpXg53Y")
faq_sheet = sheet.worksheet("FAQ")

# Контекст сообщений
context = {}

app = FastAPI()


def send_whatsapp_message(to, body):
    twilio.messages.create(
        from_=f"whatsapp:{twilio_whatsapp_number}",
        to=to,
        body=body
    )


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
        faq_data = faq_sheet.get_all_records()
        found = False
        for row in faq_data:
            keywords = row.get("Вопрос", "").lower().split("|")
            response = row.get("Ответ", "").strip()
            if any(keyword in message.lower() for keyword in keywords) and response:
                print(f"✅ Ответ по группе '{keywords[0]}': {response}")
                send_whatsapp_message(sender, response)
                found = True

        if not found:
            print("🤖 Ответа в таблице нет, обращаемся к ChatGPT...")
            chat_history = context.get(sender, [])
            chat_history.append({"role": "user", "content": message})

            gpt_response = gpt.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content":
                        "Ты — вежливый и профессиональный помощник от имени образовательного центра. "
                        "Отвечай понятно, дружелюбно и полезно по темам: курсы, цены, расписание, обучение, сертификаты."}
                ] + chat_history
            )
            reply = gpt_response.choices[0].message.content.strip()
            print(f"🤖 Ответ от ChatGPT: {reply}")
            send_whatsapp_message(sender, reply)
            chat_history.append({"role": "assistant", "content": reply})
            context[sender] = chat_history[-10:]  # Сохраняем последние 10 сообщений

        return PlainTextResponse("ok")

    except Exception as e:
        print("❌ Ошибка:", str(e))
        send_whatsapp_message(sender, "Произошла ошибка на сервере. Мы скоро всё исправим 🙏")
        return PlainTextResponse("Ошибка сервера", status_code=500)
