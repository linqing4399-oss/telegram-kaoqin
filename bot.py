import sqlite3
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ----------------- 数据库初始化 -----------------
DB_FILE = "attendance_v5.db"

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
async def is_group_admin(chat, user_id, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if chat.type in ["group", "supergroup"]:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            return chat_member.status in ["administrator", "creator"]
        except Exception as e:
            print(f"检查管理员权限失败: {e}")
            return False
    return False

# ----------------- 核心功能逻辑 -----------------

# 1. 呼出快捷控制面板按钮 (/menu 或直接在群里发送)
async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 构建按钮布局 (每行一个按钮)
    keyboard = [
        [InlineKeyboardButton("⏰ 点击：上班打卡", callback_data="btn_dk")],
        [InlineKeyboardButton("📊 点击：查询个人当月天数", callback_data="btn_cx")],
        [InlineKeyboardButton("📋 点击：全员考勤统计(限管理)", callback_data="btn_kq")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 **欢迎使用考勤快捷控制面板**\n请直接点击下方对应按钮进行操作：", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# 2. 集中处理所有按钮点击事件 (Callback Query)
async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # 必须先调用 answer() 告诉 Telegram 已经收到点击，防止按钮一直转圈圈
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "无用户名"
    full_name = user.full_name
    chat = query.message.chat
    
    today = datetime.date.today().isoformat()
    current_month = datetime.date.today().strftime("%Y-%m")

    # ---- 逻辑 A：点击了上班打卡 ----
    if query.data == "btn_dk":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO attendance VALUES (?, ?, ?, ?)", (user_id, username, full_name, today))
            conn.commit()
            # 在聊天框发送一条新消息反馈（也可以用 query.message.reply_text）
            await context.bot.send_message(chat_id=chat.id, text=f"✅ {full_name} 打卡成功")
        except sqlite3.IntegrityError:
            await context.bot.send_message(chat_id=chat.id, text=f"⚠️ {full_name}，你已经打过卡了")
        finally:
            conn.close()

    # ---- 逻辑 B：点击了查询个人天数 ----
    elif query.data == "btn_cx":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM attendance 
            WHERE user_id = ? AND date LIKE ?
        ''', (user_id, f"{current_month}%"))
        result = cursor.fetchone()
        conn.close()

        count = result[0] if result else 0
        await context.bot.send_message(chat_id=chat.id, text=f"📊 {full_name}，您本月累计上班打卡天数为：{count}天。")

    # ---- 逻辑 C：点击了全员考勤统计 ----
    elif query.data == "btn_kq":
        # 权限校验
        if not await is_group_admin(chat, user_id, context):
            await context.bot.send_message(chat_id=chat.id, text=f"❌ {full_name}，你没有查询权限")
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
            await context.bot.send_message(chat_id=chat.id, text=f"📊 {current_month} 暂无打卡记录。")
            return

        report = f"📅 **{current_month} 全员考勤统计结算**\n"
        report += "`序号 | 名字 | 打卡天数`\n"
        report += "-------------------------\n"
        for idx, row in enumerate(rows, 1):
            report += f"{idx} | {row[0]} | **{row[1]}天**\n"
        
        await context.bot.send_message(chat_id=chat.id, text=report, parse_mode="Markdown")

# ----------------- 主程序 -----------------
def main():
    init_db()
    
    # ⚠️ 请在此处替换为您真实的 Bot Token
    TOKEN = "8948616036:AAGxG8hD6-BAwE-LB2B9nM9aoFcNKSqIkx8"
    
    application = Application.builder().token(TOKEN).build()

    # 1. 注册基础命令（输入 /menu 或者 /start 弹出按钮面板）
    application.add_handler(CommandHandler("menu", send_menu))
    application.add_handler(CommandHandler("start", send_menu))
    
    # 为了防止习惯，保留原来的文字命令触发也行
    application.add_handler(CommandHandler("dk", lambda u, c: context.bot.send_message(u.effective_chat.id, "请使用 /menu 呼出面板点击按钮打卡")))
    
    # 2. 核心：注册按钮点击事件监听器
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # 启动机器人
    print("机器人已启动，内联键盘已就绪...")
    application.run_polling()

if __name__ == '__main__':
    main()
