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
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты вежливый ассистент, который отвечает клиентам через WhatsApp."},
                {"role": "user", "content": message}
            ]
        )

        reply = response.choices[0].message.content.strip()
        print(f"Ответ: {reply}")
        return PlainTextResponse(reply)
    except Exception as e:
        print("Ошибка:", str(e))
        return PlainTextResponse("Ошибка сервера", status_code=500)
