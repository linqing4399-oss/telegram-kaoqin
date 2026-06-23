import os
import sqlite3
import datetime
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------- 1. 创建一个虚假的网页服务 -----------------
# 借此满足 Render Web Service 必须有端口监听的要求
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_web_server():
    # Render 会自动分配一个 PORT 环境变量，默认如果没有就用 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ----------------- 2. 数据库配置 -----------------
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

# ----------------- 3. 机器人核心功能 -----------------
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

async def send_bot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("⏰ 上班打卡"), KeyboardButton("📊 查询我当月天数")],
        [KeyboardButton("📋 全员考勤统计(限管理)")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
    await update.message.reply_text(
        "✨ **考勤机器人专属快捷键盘已启用**\n你可以直接点击输入框下方的精美按钮进行操作：",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "无用户名"
    full_name = user.full_name
    today = datetime.date.today().isoformat()
    current_month = datetime.date.today().strftime("%Y-%m")

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

    elif text == "📊 查询我当月天数":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM attendance WHERE user_id = ? AND date LIKE ?', (user_id, f"{current_month}%"))
        result = cursor.fetchone()
        conn.close()
        count = result[0] if result else 0
        await update.message.reply_text(f"📊 {full_name}，您本月累计上班打卡天数为：{count}天。")

    elif text == "📋 全员考勤统计(限管理)":
        if not await is_group_admin(update, context):
            await update.message.reply_text("❌ 你没有查询权限")
            return
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT full_name, COUNT(*) FROM attendance WHERE date LIKE ? GROUP BY user_id ORDER BY full_name ASC', (f"{current_month}%",))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await update.message.reply_text(f"📊 {current_month} 暂无打卡记录。")
            return
        report = f"📅 **{current_month} 全员考勤统计结算**\n`序号 | 名字 | 打卡天数`\n-------------------------\n"
        for idx, row in enumerate(rows, 1):
            report += f"{idx} | {row[0]} | **{row[1]}天**\n"
        await update.message.reply_text(report, parse_mode="Markdown")

# ----------------- 4. 主入口 -----------------
def main():
    init_db()
    
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("错误：未找到系统环境变量 BOT_TOKEN！")
        return
        
    # 开启一条独立线程在后台运行虚拟网页
    threading.Thread(target=run_web_server, daemon=True).start()

    # 主线程正常运行机器人
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("menu", send_bot_menu))
    application.add_handler(CommandHandler("start", send_bot_menu))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))

    print("机器人已启动...")
    application.run_polling()

if __name__ == '__main__':
    main()
