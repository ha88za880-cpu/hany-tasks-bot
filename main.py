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
    return "Attendance Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# لو كنت غيرت التوكن من BotFather حط الجديد هنا، لو مغيرتوش سيب ده زي ما هو
BOT_TOKEN = "8764423533:AAFRwaQPHQ85ElqNBkXvCbNB-6be6jjmAm4"
bot = telebot.TeleBot(BOT_TOKEN)

def init_db():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_name TEXT,
            date TEXT,
            check_in TEXT,
            check_out TEXT,
            total_hours TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🟢 تسجيل حضور", "🔴 تسجيل انصراف")
    markup.row("📊 تقرير الحضور (Excel)")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "أهلاً يا بشمهندس! بوت الحضور والانصراف الخاص بشركة القبائلي للصناعات الغذائية (فرع مدينة السادات) جاهز للعمل.", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "🟢 تسجيل حضور")
def check_in_start(message):
    msg = bot.send_message(message.chat.id, "اكتب اسم العامل أو الموظف المراد تسجيل حضوره:")
    bot.register_next_step_handler(msg, save_check_in)

def save_check_in(message):
    worker_name = message.text
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")
    
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO attendance (worker_name, date, check_in, check_out, total_hours, status) VALUES (?, ?, ?, ?, ?, ?)",
                   (worker_name, today, now_time, "--", "--", "حاضر"))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"✅ تم تسجيل حضور لـ ({worker_name}) الساعة {now_time}", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "🔴 تسجيل انصراف")
def check_out_start(message):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, worker_name FROM attendance WHERE date = ? AND check_out = '--'", (today,))
    records = cursor.fetchall()
    conn.close()

    if not records:
        bot.send_message(message.chat.id, "لا توجد أسماء مسجلة بحضور اليوم وتنتظر الانصراف!", reply_markup=main_menu())
        return

    markup = types.InlineKeyboardMarkup()
    for rec in records:
        markup.add(types.InlineKeyboardButton(f"انصراف لـ: {rec[1]} 🔴", callback_data=f"out|{rec[0]}"))
    
    bot.send_message(message.chat.id, "اختر العامل لتسجيل وقت انصرافه:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("out|"))
def process_checkout(call):
    rec_id = call.data.split("|")[1]
    now_time = datetime.now().strftime("%H:%M")
    
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT check_in, worker_name FROM attendance WHERE id = ?", (rec_id,))
    res = cursor.fetchone()
    
    if res:
        check_in_time, worker_name = res[0], res[1]
        try:
            FMT = "%H:%M"
            tdelta = datetime.strptime(now_time, FMT) - datetime.strptime(check_in_time, FMT)
            hours = round(tdelta.total_seconds() / 3600, 1)
            total_str = f"{hours} ساعة"
        except:
            total_str = "مكتمل"

        cursor.execute("UPDATE attendance SET check_out = ?, total_hours = ? WHERE id = ?", (now_time, total_str, rec_id))
        conn.commit()
        
        bot.edit_message_text(f"🔴 تم تسجيل انصراف ({worker_name}) الساعة {now_time} (إجمالي: {total_str})", 
                              call.message.chat.id, call.message.message_id)
    conn.close()

@bot.message_handler(func=lambda msg: msg.text == "📊 تقرير الحضور (Excel)")
def export_attendance(message):
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT worker_name, date, check_in, check_out, total_hours, status FROM attendance")
    rows = cursor.fetchall()
    conn.close()
    
    file_path = "Attendance_Report.csv"
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["اسم العامل", "التاريخ", "الحضور", "الانصراف", "ساعات العمل", "الحالة"])
        writer.writerows(rows)
    
    with open(file_path, "rb") as f:
        bot.send_document(message.chat.id, f, caption="📊 تقرير حضور وانصراف الموقع جاهز", reply_markup=main_menu())

if __name__ == "__main__":
    bot.remove_webhook()
    Thread(target=run_web).start()
    bot.infinity_polling(skip_pending=True)
