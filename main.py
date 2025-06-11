from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os
import openai

# Загружаем ключ из .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        # Ответ от ChatGPT
        response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "Ты — вежливый и профессиональный помощник, представляющий образовательный центр. Отвечай на вопросы клиентов подробно, грамотно и дружелюбно. Предлагай помощь, рассказывай о курсах, расписании, оплате, преподавателях. Будь доброжелательным, отвечай так, как если бы ты был живым сотрудником центра."},
        {"role": "user", "content": message}
    ]
)


        reply = response.choices[0].message.content.strip()
        print(f"Ответ: {reply}")
        return PlainTextResponse(reply)
    except Exception as e:
        print("Ошибка:", str(e))
        return PlainTextResponse("Ошибка сервера", status_code=500)
