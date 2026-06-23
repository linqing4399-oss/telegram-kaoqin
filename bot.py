import sqlite3
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ----------------- 数据库初始化 -----------------
DB_FILE = "attendance_v4.db"

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

# ----------------- 核心功能逻辑 -----------------

# 1. 上班打卡 (/dk)
async def start_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "无用户名"
    full_name = user.full_name
    today = datetime.date.today().isoformat()       # 格式：YYYY-MM-DD

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO attendance VALUES (?, ?, ?, ?)", (user_id, username, full_name, today))
        conn.commit()
        await update.message.reply_text("打卡成功")
    except sqlite3.IntegrityError:
        # 主键冲突说明今天已经打过卡了
        await update.message.reply_text("你已经打过卡了")
    finally:
        conn.close()

# 2. 查询自己当月上班天数 (/cx)
async def check_self_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    full_name = update.effective_user.full_name
    current_month = datetime.date.today().strftime("%Y-%m") # 格式：YYYY-MM

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

# 3. 考勤总统计 (/kq) —— 区分管理员权限
async def admin_check_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 权限检查：如果不是管理员，直接提示没有权限
    if not await is_group_admin(update, context):
        await update.message.reply_text("你没有查询权限")
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

    # 按照要求的格式排版
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

    # 绑定命令处理器
    application.add_handler(CommandHandler("dk", start_attendance))   # 所有人打卡
    application.add_handler(CommandHandler("cx", check_self_status))  # 所有人查自己
    application.add_handler(CommandHandler("kq", admin_check_all))     # 全员统计（内置权限校验）

    # 启动机器人
    print("机器人已启动，正在监听群聊命令...")
    application.run_polling()

if __name__ == '__main__':
    main()
