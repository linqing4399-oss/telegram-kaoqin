import os
import sqlite3
import datetime
import asyncio
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= 1. 虚拟网页服务 (应对 Render 检查) =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_web_server():
    # Render 会自动分配一个 PORT 环境变量，如果没有就默认用 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ================= 2. 数据库配置 (保存在 Render 永久硬盘卷) =================
if os.path.exists('/data'):
    DB_FILE = "/data/attendance_v6.db"
else:
    DB_FILE = "attendance_v6.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            date TEXT,
            PRIMARY KEY (user_id, date)
        )
    ''')
    conn.commit()
    conn.close()

# ================= 3. 考勤业务逻辑 =================

# 检查管理员权限
async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user_id = update.effective_user.id
    if chat.type in ["group", "supergroup"]:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            return chat_member.status in ["administrator", "creator"]
        except Exception as e:
            print(f"检查管理员权限失败: {e}")
            return False
    return False

# 呼出底部常驻美化键盘菜单
async def send_bot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("⏰ 上班打卡"), KeyboardButton("📊 查询我当月天数")],
        [KeyboardButton("📋 全员考勤统计(限管理)")]
    ]
    # 使用 is_persistent 让菜单常驻在输入框下方
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
    await update.message.reply_text(
        "✨ **考勤机器人专属快捷键盘已启用**\n你可以直接点击输入框下方的精美按钮进行操作：",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# 核心处理：根据按钮文字执行相应功能
async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "无用户名"
    full_name = user.full_name
    today = datetime.date.today().isoformat()
    current_month = datetime.date.today().strftime("%Y-%m")

    # A. 触发打卡
    if text == "⏰ 上班打卡":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO attendance VALUES (?, ?, ?, ?)", (user_id, username, full_name, today))
            conn.commit()
            await update.message.reply_text("✅ 打卡成功")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠️ 你已经打过卡了")
        finally:
            conn.close()

    # B. 触发查询自己
    elif text == "📊 查询我当月天数":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM attendance WHERE user_id = ? AND date LIKE ?', (user_id, f"{current_month}%"))
        result = cursor.fetchone()
        conn.close()
