import os
import sqlite3
import datetime
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ----------------- 数据库初始化 -----------------
DB_FILE = "attendance_v2.db"

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

# 管理员指令 /cx ：查询所有人当月的上班天数（按字母A-Z排序）
async def admin_check_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 权限检查
    if not await is_group_admin(update, context):
        await update.message.reply_text("❌ 抱歉，该命令仅限群管理员在群组中使用。")
        return

    current_month = datetime.date.today().strftime("%Y-%m")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 筛选当月数据，按 full_name (名字) 字母 A-Z 排序
    cursor.execute('''
        SELECT full_name, username, COUNT(*) 
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

    report = f"📊 **{current_month} 全员考勤统计（按字母排序）**\n"
    report += "-------------------------\n"
    for idx, row in enumerate(rows, 1):
        report += f"{idx}. {row[0]} ({row[1]}): **{row[2]}天**\n"
    
    await update.message.reply_text(report, parse_mode="Markdown")

# 管理员指令 /export ：月底统计并导出 Excel 表格
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 权限检查
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
        await update.message.reply_text("❌ 本月没有任何打卡数据，无法导出。")
        return

    # 构建符合要求的格式：第一列序号，第二列名字，第三列打卡天数
    data = []
    for idx, row in enumerate(rows, 1):
        data.append({
            "序号": idx,
            "名字": row[0],
            "打卡天数": row[1]
        })

    # 使用 pandas 转换为数据表并导出为 Excel
    df = pd.DataFrame(data)
    file_name = f"考勤统计_{current_month}.xlsx"
    
    # 保存为本地文件
    df.to_excel(file_name, index=False)

    # 发送文件给群组
    try:
        with open(file_name, "rb") as excel_file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=excel_file,
                caption=f"📅 {current_month} 月底考勤统计表格已生成。"
            )
        # 发送完后删除本地临时文件，节约空间
        os.remove(file_name)
    except Exception as e:
        await update.message.reply_text(f"❌ 导出文件失败: {e}")

# ----------------- 主程序 -----------------
def main():
    init_db()
    
    # ⚠️ 替换为你的真实 Bot Token
    TOKEN = "8948616036:AAGxG8hD6-BAwE-LB2B9nM9aoFcNKSqIkx8"
    
    application = Application.builder().token(TOKEN).build()

    # 监听普通文本消息（处理 “上班” 和 “查询”）
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    # 监听管理员指令
    application.add_handler(CommandHandler("cx", admin_check_all))   # 管理员输入 /cx 查询所有人
    application.add_handler(CommandHandler("export", export_excel))  # 管理员输入 /export 导出 Excel

    # 启动机器人
    print("机器人已启动，正在监听群聊消息...")
    application.run_polling()

if __name__ == '__main__':
    main()
