from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)
app = FastAPI()

@app.get("/")
def root():
    return {"status": "Bot is running ✅"}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    form_data = await request.form()
    message = form_data.get("Body", "")
    sender = form_data.get("From", "")

    print(f"Получено сообщение от {sender}: {message}")

    if not message:
        return PlainTextResponse("Нет текста", status_code=400)

    try:
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
        print(f"Ответ: {reply}")
        return PlainTextResponse(reply)

    except Exception as e:
        print("Ошибка:", str(e))
        return PlainTextResponse("Ошибка сервера", status_code=500)

