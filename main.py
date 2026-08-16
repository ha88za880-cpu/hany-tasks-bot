import os
import sqlite3
import csv
import time
from threading import Thread
from datetime import datetime
from flask import Flask
import telebot
from telebot import types

app = Flask(__name__)

@app.route('/')
def home():
    return "Task Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

BOT_TOKEN = "8024260311:AAEBr2g5fzJwJQv4STgVnLfULq6BdQC_Gsg"
bot = telebot.TeleBot(BOT_TOKEN)

# قاعدة بيانات مهام اليوم
def init_db():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS daily_log (id INTEGER PRIMARY KEY AUTOINCREMENT, task_name TEXT, date TEXT, status TEXT)")
    conn.commit()
    conn.close()

init_db()
user_states = {} # لحفظ حالة المستخدم (إضافة مهام)

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ إضافة مهام اليوم", "📝 مراجعة المهام")
    markup.row("📊 تقرير إنجاز الشهر")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "أهلاً هاني، جاهز ليوم إنتاجية عالي؟", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "➕ إضافة مهام اليوم")
def add_task_mode(message):
    user_states[message.chat.id] = "adding"
    bot.send_message(message.chat.id, "اكتب مهامك اليوم، كل مهمة في رسالة. لما تخلص اكتب: /done")

@bot.message_handler(func=lambda msg: msg.text == "/done")
def finish_adding(message):
    user_states[message.chat.id] = "idle"
    bot.send_message(message.chat.id, "تم حفظ المهام! تقدر تبدأ المراجعة من القائمة.", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "adding")
def save_task(message):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO daily_log (task_name, date, status) VALUES (?, ?, ?)", (message.text, today, "بانتظار التنفيذ"))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ تم إضافة: " + message.text)

@bot.message_handler(func=lambda msg: msg.text == "📝 مراجعة المهام")
def review_tasks(message):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, task_name FROM daily_log WHERE date = ? AND status = 'بانتظار التنفيذ'", (today,))
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        bot.send_message(message.chat.id, "لا توجد مهام جديدة اليوم!")
        return
    
    for task in tasks:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("تمت ✅", callback_data=f"done|{task[0]}"),
                   types.InlineKeyboardButton("لم تُنفذ ❌", callback_data=f"fail|{task[0]}"))
        bot.send_message(message.chat.id, f"📌 {task[1]}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    task_id = call.data.split("|")[1]
    status = "تمت" if call.data.startswith("done") else "لم تُنفذ"
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE daily_log SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()
    bot.edit_message_text(f"{call.message.text} -> {status}", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: msg.text == "📊 تقرير إنجاز الشهر")
def report(message):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_log")
    rows = cursor.fetchall()
    conn.close()
    
    # تحويل لملف CSV
    file_path = "Monthly_Report.csv"
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["المهمة", "التاريخ", "الحالة"])
        writer.writerows([(r[1], r[2], r[3]) for r in rows])
    
    with open(file_path, "rb") as f:
        bot.send_document(message.chat.id, f)

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling()
