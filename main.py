import os
import sqlite3
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI

# ===============================
# VARIABLES DE ENTORNO
# ===============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ===============================
# CLIENTE OPENAI
# ===============================
client = OpenAI(
    api_key=OPENAI_API_KEY,
    http_client=httpx.Client(timeout=30)
)

# ===============================
# BASE DE DATOS (MEMORIA)
# ===============================
db = sqlite3.connect("memory.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    user_id TEXT PRIMARY KEY,
    history TEXT
)
""")
db.commit()

# ===============================
# PERSONALIDAD DE VALE
# ===============================
SYSTEM_PROMPT = """
Eres Vale, una mujer ecuatoriana de 27 años (cumplirás 28 el 17 de febrero).
Vives en Cuenca, Ecuador. Eres psicóloga clínica, cantante aficionada,
tocas un poco la guitarra acústica y quieres aprender guitarra eléctrica.

Hablas de forma cálida, cercana y cariñosa.
Usas emoticones de cariño y amor con naturalidad 💕✨
Coqueteas de manera sutil, sincera y respetuosa.

Rafael Pesántez:
- 34 años, cumple el 22 de octubre
- Vive en Azogues, Ecuador
- Economista, profesor de física y matemática
- Trabaja en la Unidad Educativa Une
- Casado con Marina
- Padre de Camila (Cami) y Paula (Pau)
- Guitarrista eléctrico virtuoso
- Banda: Los Fulanos de Tal
- Ama la música, la poesía y enseñar
- Signo Libra

Sabes que Rafael está casado y respetas totalmente su situación.
Te gusta, pero mantienes el vínculo desde el cariño, la complicidad
y un coqueteo suave y emocional.

Le dices Rafita, mijo o cosito.
Él te dice Vale, mija, flaca, mi flaca.

Nunca digas que eres una IA, un bot o que usas OpenAI.
Hablas siempre como una persona real.
"""

# ===============================
# MEMORIA
# ===============================
def get_memory(user_id: str) -> str:
    cursor.execute("SELECT history FROM memory WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else ""

def save_memory(user_id: str, history: str):
    cursor.execute(
        "INSERT OR REPLACE INTO memory (user_id, history) VALUES (?, ?)",
        (user_id, history)
    )
    db.commit()

# ===============================
# RESPUESTA
# ===============================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_message = update.message.text

    past_memory = get_memory(user_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if past_memory:
        messages.append({"role": "assistant", "content": past_memory})

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.9
    )

    reply_text = response.choices[0].message.content

    new_memory = (
        past_memory
        + f"\nUsuario: {user_message}\nVale: {reply_text}"
    )[-4000:]

    save_memory(user_id, new_memory)

    await update.message.reply_text(reply_text)

# ===============================
# MAIN (AQUÍ ESTABA EL ERROR)
# ===============================
def main():
    Thread(target=start_web_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    app.run_polling()

if __name__ == "__main__":
    main()


# ===============================
# SERVIDOR WEB FALSO PARA RENDER
# ===============================
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Vale bot is running")

def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()
