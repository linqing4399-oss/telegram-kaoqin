import sqlite3
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------- 数据库初始化 -----------------
DB_FILE = "attendance_v3.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 创建打卡记录表
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

# ----------------- 核心功能逻辑 -----------------

# 检查用户是否为群管理员
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

# 处理普通文本消息（“上班” 和 “查询”）
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "无用户名"
    full_name = user.full_name
    today = datetime.date.today().isoformat()       # 格式：YYYY-MM-DD
    current_month = datetime.date.today().strftime("%Y-%m") # 格式：YYYY-MM

    # 1. 上班打卡逻辑
    if text == "上班":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO attendance VALUES (?, ?, ?, ?)", (user_id, username, full_name, today))
            conn.commit()
            await update.message.reply_text("打卡成功")
        except sqlite3.IntegrityError:
            # 主键冲突（同一个user_id在同一天只能有一条记录）
            await update.message.reply_text("你已经打过卡了")
        finally:
            conn.close()

    # 2. 个人查询当月天数逻辑
    elif text == "查询":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # 筛选该用户在当月的打卡记录
        cursor.execute('''
            SELECT COUNT(*) FROM attendance 
            WHERE user_id = ? AND date LIKE ?
        ''', (user_id, f"{current_month}%"))
        result = cursor.fetchone()
        conn.close()

        count = result[0] if result else 0
        await update.message.reply_text(f"📊 {full_name}，您本月累计上班打卡天数为：{count}天。")

# 管理员指令 /cx ：随时查询所有人当月的上班天数（按字母A-Z排序）
async def admin_check_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_group_admin(update, context):
        await update.message.reply_text("❌ 抱歉，该命令仅限群管理员在群组中使用。")
        return

    current_month = datetime.date.today().strftime("%Y-%m")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 筛选当月数据，按 full_name (名字) 字母 A-Z 排序
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

    report = f"📊 **{current_month} 全员考勤实时统计（A-Z排序）**\n"
    report += "-------------------------\n"
    for idx, row in enumerate(rows, 1):
        report += f"{idx}. {row[0]} : **{row[1]}天**\n"
    
    await update.message.reply_text(report, parse_mode="Markdown")

# 管理员指令 /report ：月底统计每人每月上班天数（文本报表形式）
async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_group_admin(update, context):
        await update.message.reply_text("❌ 抱歉，该命令仅限群管理员在群组中使用。")
        return

    current_month = datetime.date.today().strftime("%Y-%m")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 获取当月所有人的打卡天数，按名字 A-Z 排序
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
        await update.message.reply_text(f"❌ {current_month} 没有任何打卡数据，无法生成报表。")
        return

    # 生成符合格式要求的文本：第一列序号，第二列名字，第三列打卡天数
    report = f"📅 **{current_month} 月底全员考勤统计结算**\n"
    report += "`序号 | 名字 | 打卡天数`\n"
    report += "-------------------------\n"
    
    for idx, row in enumerate(rows, 1):
        report += f"{idx} | {row[0]} | **{row[1]}天**\n"

    await update.message.reply_text(report, parse_mode="Markdown")

# ----------------- 主程序 -----------------
def main():
    init_db()
    
    # ⚠️ 替换为你的真实 Bot Token
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    application = Application.builder().token(TOKEN).build()

    # 监听普通文本消息（处理 “上班” 和 “查询”）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    # 监听管理员指令
    application.add_handler(CommandHandler("cx", admin_check_all))       # 管理员输入 /cx 随时群查
    application.add_handler(CommandHandler("report", monthly_report))   # 管理员输入 /report 月底结算统计

    # 启动机器人
    print("机器人已启动，正在监听群聊消息...")
    application.run_polling()

if __name__ == '__main__':
    main()
