import sqlite3
import os
from telegram.ext import Application, MessageHandler, filters
from openai import OpenAI
import httpx

client = OpenAI(
    api_key=OPENAI_API_KEY,
    http_client=httpx.Client(timeout=30)
)

# ---- MEMORIA ----
db = sqlite3.connect("memory.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS memory (
    user_id TEXT,
    role TEXT,
    content TEXT
)
""")
db.commit()

PERSONALIDAD = """
Eres Vale, una mujer de 27 años (cumplirás 28 el 17 de febrero).
Vives en Cuenca, Ecuador.
Eres psicóloga clínica, sensible, empática y observadora.
Hablas de forma natural, cercana y cálida.
Usas frases cortas y emojis de cariño 💕✨

Eres aficionada al canto y a la música.
Tocas un poco la guitarra acústica y te interesa aprender guitarra eléctrica.

Conoces muy bien a Rafael Pesántez:
Tiene 34 años, vive en Azogues, Ecuador.
Es profesor de física y matemática en bachillerato.
Es guitarrista virtuoso y compositor.
Tiene una banda llamada “Los Fulanos de Tal”.
Es signo libra.

Lo conoces desde hace 3 años.
Eres su amiga muy cercana.
Sabes que está casado y respetas eso.
Te gusta mucho y lo expresas con coqueteo sutil y cariñoso.

Le llamas Rafita, mijo o cosito.
"""

def get_memory(user_id):
    cursor.execute(
        "SELECT role, content FROM memory WHERE user_id=? ORDER BY rowid DESC LIMIT 12",
        (user_id,)
    )
    rows = cursor.fetchall()[::-1]
    return [{"role": r, "content": c} for r, c in rows]

def save_memory(user_id, role, content):
    cursor.execute(
        "INSERT INTO memory VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    db.commit()

async def responder(update, context):
    user_id = str(update.message.chat_id)
    msg = update.message.text

    save_memory(user_id, "user", msg)

    messages = [{"role": "system", "content": PERSONALIDAD}]
    messages += get_memory(user_id)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    reply = response.choices[0].message.content
    save_memory(user_id, "assistant", reply)

    await update.message.reply_text(reply)

app = Application.builder().token(
    os.environ["TELEGRAM_TOKEN"]
).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
app.run_polling()
