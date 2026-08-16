import os
import sqlite3
import csv
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

# قائمة المهام الجاهزة اللي بتكررها دايما
DEFAULT_TASKS = ["قراءة تقارير", "مراجعة حضور الموظفين", "متابعة السلامة المهنية", "تحديث ملفات الإكسيل"]

def init_db():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS daily_log (id INTEGER PRIMARY KEY AUTOINCREMENT, task_name TEXT, date TEXT, status TEXT)")
    conn.commit()
    conn.close()

init_db()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 مهام جاهزة", "➕ إضافة مهمة جديدة")
    markup.row("📝 مراجعة مهام اليوم", "📊 تقرير الشهر")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "أهلاً يا هاني، اختار المهمة اللي عايز تضيفها:", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "📋 مهام جاهزة")
def show_default_tasks(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for task in DEFAULT_TASKS:
        markup.add(task)
    markup.add("⬅️ رجوع")
    bot.send_message(message.chat.id, "اختار مهمة من القائمة:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in DEFAULT_TASKS)
def save_default_task(message):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO daily_log (task_name, date, status) VALUES (?, ?, ?)", (message.text, today, "بانتظار التنفيذ"))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ تم إضافة: {message.text} لقائمة اليوم", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "➕ إضافة مهمة جديدة")
def add_new_task_mode(message):
    msg = bot.send_message(message.chat.id, "اكتب اسم المهمة الجديدة:")
    bot.register_next_step_handler(msg, save_new_task)

def save_new_task(message):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO daily_log (task_name, date, status) VALUES (?, ?, ?)", (message.text, today, "بانتظار التنفيذ"))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ تم حفظ المهمة الجديدة!", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "📝 مراجعة مهام اليوم")
def review_tasks(message):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, task_name FROM daily_log WHERE date = ? AND status = 'بانتظار التنفيذ'", (today,))
    tasks = cursor.fetchall()
    conn.close()
    if not tasks:
        bot.send_message(message.chat.id, "لا توجد مهام اليوم!", reply_markup=main_menu())
        return
    for task in tasks:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("تمت ✅", callback_data=f"done|{task[0]}"))
        bot.send_message(message.chat.id, f"📌 {task[1]}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    task_id = call.data.split("|")[1]
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE daily_log SET status = 'تمت' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    bot.edit_message_text(f"{call.message.text} -> تم الإنجاز! ✅", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda msg: msg.text == "⬅️ رجوع" or msg.text == "📊 تقرير الشهر")
def handle_other(message):
    if message.text == "📊 تقرير الشهر":
        # كود التقرير هنا...
        bot.send_message(message.chat.id, "تم تجهيز التقرير...", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "تم الرجوع:", reply_markup=main_menu())

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling()
