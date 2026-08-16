import os
import sqlite3
import csv
import time
from threading import Thread
from datetime import datetime
from flask import Flask
import telebot
from telebot import types

# سيرفر ويب داخلي للتشغيل المجاني على Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Task Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# توكن بوت المهام الخاص بك
BOT_TOKEN = "8024260311:AAEBr2g5fzJwJQv4STgVnLfULq6BdQC_Gsg"
bot = telebot.TeleBot(BOT_TOKEN)

# إعداد قاعدة البيانات للمهام
def init_db():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS my_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM my_tasks")
    if cursor.fetchone()[0] == 0:
        sample_tasks = [
            ("قراءة صفحة قرآن",),
            ("رياضة لمدة 30 دقيقة",),
            ("مراجعة مهام الشغل",),
            ("تعلم برمجة ساعة",)
        ]
        cursor.executemany("INSERT INTO my_tasks (task_name) VALUES (?)", sample_tasks)
    conn.commit()
    conn.close()

init_db()
active_sessions = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📝 مراجعة مهام اليوم")
    markup.row("📊 تقرير إنجاز الشهر")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "🎯 أهلاً بك يا هاني في بوت إدارة مهامك الشخصية!\n\n"
        "اختر من الأزرار بالأسفل:",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda msg: msg.text == "📝 مراجعة مهام اليوم")
def start_daily_tasks(message):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task_name FROM my_tasks")
    tasks = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not tasks:
        bot.send_message(message.chat.id, "⚠️ لا توجد مهام مسجلة.")
        return

    active_sessions[message.chat.id] = {
        "tasks": tasks,
        "current_index": 0
    }
    ask_next_task(message.chat.id)

def ask_next_task(chat_id):
    session = active_sessions.get(chat_id)
    if not session:
        return

    idx = session["current_index"]
    if idx < len(session["tasks"]):
        task_name = session["tasks"][idx]
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("تمت ✅", callback_data=f"tstatus|{task_name}|تمت"),
            types.InlineKeyboardButton("لم تُنفذ ❌", callback_data=f"tstatus|{task_name}|لم تنفذ")
        )
        bot.send_message(
            chat_id, 
            f"مهمة ({idx + 1}/{len(session['tasks'])}):\n📌 **{task_name}**\n\nهل أنجزت هذه المهمة اليوم؟", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
    else:
        bot.send_message(chat_id, "🎉 ممتاز يا هاني! أنهيت مراجعة مهام اليوم وتسجيلها بنجاح.", reply_markup=main_menu())
        del active_sessions[chat_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("tstatus|"))
def handle_task_callback(call):
    _, task_name, status = call.data.split("|")
    today_date = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO daily_log (task_name, date, status) VALUES (?, ?, ?)", (task_name, today_date, status))
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, text=f"تم تسجيل: {status}")
    bot.edit_message_text(f"📌 {task_name}: **{status}**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

    if call.message.chat.id in active_sessions:
        active_sessions[call.message.chat.id]["current_index"] += 1
        ask_next_task(call.message.chat.id)

@bot.message_handler(func=lambda msg: msg.text == "📊 تقرير إنجاز الشهر")
def handle_monthly_report(message):
    try:
        conn = sqlite3.connect("tasks.db")
        cursor = conn.cursor()
        cursor.execute("SELECT task_name, date, status FROM daily_log")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            bot.send_message(message.chat.id, "⚠️ لا توجد سجلات مسجلة حتى الآن.")
            return

        file_path = f"Monthly_Report_{datetime.now().strftime('%Y_%m')}.csv"
        with open(file_path, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(["المهمة", "التاريخ", "الحالة"])
            writer.writerows(rows)

        with open(file_path, "rb") as doc:
            bot.send_document(message.chat.id, doc, caption="📊 تقرير إنجاز المهام الشهري (جاهز للإكسيل)")

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        bot.send_message(message.chat.id, f"حدث خطأ: {e}")

if __name__ == "__main__":
    server_thread = Thread(target=run_web)
    server_thread.daemon = True
    server_thread.start()
    
    print("Task Bot is running...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Retrying... Error: {e}")
            time.sleep(5)
