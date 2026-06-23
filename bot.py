import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------- 数据库初始化 -----------------
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

# ----------------- 辅助函数：检查管理员权限 -----------------
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

# ----------------- 呼出底部常驻美化菜单 -----------------
async def send_bot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 这里定义底部键盘的样式和排版（第一排两个按钮，第二排一个大按钮）
    keyboard = [
        [KeyboardButton("⏰ 上班打卡"), KeyboardButton("📊 查询我当月天数")],
        [KeyboardButton("📋 全员考勤统计(限管理)")]
    ]
    
    # resize_keyboard=True 让按钮自动适应手机屏幕高度，不至于铺满半个屏幕
    # persistent=True 让它常驻在聊天框下方
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
    
    await update.message.reply_text(
        "✨ **考勤机器人专属快捷键盘已启用**\n你可以直接点击输入框下方的精美按钮进行操作：",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ----------------- 核心功能逻辑（通过识别按钮上的文字触发） -----------------
async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "无用户名"
    full_name = user.full_name
    today = datetime.date.today().isoformat()
    current_month = datetime.date.today().strftime("%Y-%m")

    # 1. 触发打卡
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

    # 2. 触发查询自己
    elif text == "📊 查询我当月天数":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM attendance 
            WHERE user_id = ? AND date LIKE ?
        ''', (user_id, f"{current_month}%"))
        result = cursor.fetchone()
        conn.close()

        count = result[0] if result else 0
        await update.message.reply_text(f"📊 {full_name}，您本月累计上班打卡天数为：{count}天。")

    # 3. 触发考勤统计
    elif text == "📋 全员考勤统计(限管理)":
        if not await is_group_admin(update, context):
            await update.message.reply_text("❌ 你没有查询权限")
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT full_name, COUNT(*) 
            FROM attendance 
            WHERE date LIKE ? 
            GROUP BY user_id 
            ORDER BY full_name ASC
        ''', (f"{current_month}%",))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text(f"📊 {current_month} 暂无打卡记录。")
            return

        report = f"📅 **{current_month} 全员考勤统计结算**\n"
        report += "`序号 | 名字 | 打卡天数`\n"
        report += "-------------------------\n"
        for idx, row in enumerate(rows, 1):
            report += f"{idx} | {row[0]} | **{row[1]}天**\n"
        
        await update.message.reply_text(report, parse_mode="Markdown")

# ----------------- 主程序 -----------------
def main():
    init_db()
    
    # ⚠️ 请在此处替换为您真实的 Bot Token
    TOKEN = "8948616036:AAGxG8hD6-BAwE-LB2B9nM9aoFcNKSqIkx8"
    
    application = Application.builder().token(TOKEN).build()

    # 注册命令来呼出这个自定义底部键盘
    application.add_handler(CommandHandler("menu", send_bot_menu))
    application.add_handler(CommandHandler("start", send_bot_menu))
    
    # 监听所有的文本消息（当用户点击自定义键盘时，等同于发出了对应的文本）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))

    # 启动机器人
    print("底部精美快捷键盘机器人已启动...")
    application.run_polling()

if __name__ == '__main__':
    main()
