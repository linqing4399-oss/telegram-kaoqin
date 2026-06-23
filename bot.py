import sqlite3
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------- 数据库初始化 -----------------
DB_FILE = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 创建打卡记录表（只记录上班）
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

# 处理“上班”打卡消息
async def handle_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "上班":
        user = update.effective_user
        user_id = user.id
        username = f"@{user.username}" if user.username else "无用户名"
        full_name = user.full_name
        today = datetime.date.today().isoformat() # 格式化为 YYYY-MM-DD
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 尝试插入今日打卡记录
            cursor.execute("INSERT INTO attendance VALUES (?, ?, ?, ?)", (user_id, username, full_name, today))
            conn.commit()
            await update.message.reply_text(f"✅ {full_name} ({username}) 打卡成功！\n📅 日期：{today}\n💪 今天也要加油哦！")
        except sqlite3.IntegrityError:
            # 触发主键冲突说明今天已经打过卡了
            await update.message.reply_text(f"⚠️ {full_name}，你今天已经打过卡啦，明天再来吧！")
        finally:
            conn.close()

# 查询打卡天数（区分管理员和普通成员）
async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id
    full_name = update.effective_user.full_name
    
    # 默认假设不是管理员
    is_admin = False
    
    # 如果是在群组中，检查发送者是否为管理员
    if chat.type in ["group", "supergroup"]:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user_id)
            if chat_member.status in ["administrator", "creator"]:
                is_admin = True
        except Exception as e:
            print(f"检查管理员权限失败: {e}")
            
    # 或者是你在私聊机器人（私聊默认也视作可以查自己，或者可以根据需要开放）
    elif chat.type == "private":
        # 如果是私聊，我们默认只让他查自己
        is_admin = False

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. 权限判断：如果是群管理员，展示所有人排行榜
    if is_admin:
        cursor.execute('''
            SELECT full_name, username, COUNT(*) 
            FROM attendance 
            GROUP BY user_id 
            ORDER BY COUNT(*) DESC
        ''')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("📊 暂无打卡记录。")
            return

        report = "📊 **【管理员专用】全员考勤总天数排行榜**\n"
        report += "-------------------------\n"
        for idx, row in enumerate(rows, 1):
            report += f"{idx}. {row[0]} ({row[1]}): **{row[2]}天**\n"
        
        await update.message.reply_text(report, parse_mode="Markdown")

    # 2. 如果是普通成员，只展示他自己的打卡天数
    else:
        cursor.execute('''
            SELECT COUNT(*) FROM attendance WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()

        count = result[0] if result else 0
        await update.message.reply_text(f"📊 {full_name}，您目前累计上班打卡天数为：**{count}天**。", parse_mode="Markdown")


# 月底统计（同样限制仅管理员可用）
async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    # 检查管理员权限
    if chat.type in ["group", "supergroup"]:
        chat_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user_id)
        if chat_member.status not in ["administrator", "creator"]:
            await update.message.reply_text("❌ 抱歉，`/report` 月底统计命令仅限群管理员使用。")
            return
    else:
        await update.message.reply_text("❌ 该命令只能在群组中由管理员执行。")
        return

    current_month = datetime.date.today().strftime("%Y-%m") # 格式 YYYY-MM
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 筛选当月的打卡数据
    cursor.execute('''
        SELECT full_name, username, COUNT(*) 
        FROM attendance 
        WHERE date LIKE ? 
        GROUP BY user_id 
        ORDER BY COUNT(*) DESC
    ''', (f"{current_month}%",))
    rows = cursor.fetchall()
    conn.close()

    report = f"📅 **{current_month} 月底考勤统计**\n"
    report += "-------------------------\n"
    
    if not rows:
        report += "本月无打卡记录。"
    else:
        for idx, row in enumerate(rows, 1):
            report += f"{idx}. {row[0]} ({row[1]}): **{row[2]}天**\n"
            
    await update.message.reply_text(report, parse_mode="Markdown")

# ----------------- 主程序 -----------------
def main():
    init_db()
    
    # 替换为你的真实 Bot Token
    TOKEN = "8924411075:AAEpy5a0IlVAGJCH2CtOMRERO8eGCFMEsCE"
    
    application = Application.builder().token(TOKEN).build()

    # 监听文本消息：如果文本精确匹配“上班”，触发打卡
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_attendance))
    
    # 监听命令
    application.add_handler(CommandHandler("check", check_status))   # 查天数（根据身份自动切换）
    application.add_handler(CommandHandler("report", monthly_report)) # 月底统计（仅限管理员）

    # 启动机器人
    print("机器人已启动，正在监听消息...")
    application.run_polling()

if __name__ == '__main__':
    main()
