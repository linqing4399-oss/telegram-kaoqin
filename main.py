import os
import logging
from threading import Thread
from flask import Flask, render_template_string
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. 启用日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. 内存账本
ledger = {}

# ---- TELEGRAM 机器人逻辑 ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('👋 记账机器人已在云端启动！\n\n直接输入 `+10000` 或 `-5000` 记账。\n输入 `/cx` 查询总额。')

async def handle_bookkeeping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    if chat_id not in ledger:
        ledger[chat_id] = 0
    try:
        amount = int(text)
        ledger[chat_id] += amount
        sign = "+" if amount > 0 else ""
        await update.message.reply_text(f"✅ 已记录: {sign}{amount:,} 韩元\n💰 当前总额: {ledger[chat_id]:,} 韩元")
    except ValueError:
        return

async def query_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    total = ledger.get(chat_id, 0)
    await update.message.reply_text(f"📊 当前累计总额：{total:,} 韩元")

def run_bot():
    """运行 Telegram 机器人的函数"""
    # 从环境变量中读取 Token，避免代码泄露
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ 错误: 未找到环境变量 BOT_TOKEN")
        return
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cx", query_total))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bookkeeping))
    
    print("🤖 Telegram Bot 正在后台运行...")
    app.run_polling()

# ---- FLASK 网页伪装逻辑 ----
flask_app = Flask(__name__)

# 精美的伪装网页 HTML 模板（伪装成一个极简的云端数据监控台）
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cloud Service Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); text-align: center; max-width: 400px; }
        h1 { color: #38bdf8; margin-top: 0; font-size: 1.5rem; }
        p { color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }
        .status { inline-size: auto; background: #065f46; color: #34d399; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; display: inline-block; margin-top: 1rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>System Status Overview</h1>
        <p>All cloud node services, automated pipelines, and background sync worker threads are running normally.</p>
        <div class="status">● SERVICE ONLINE</div>
    </div>
</body>
</html>
"""

@flask_app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    # 1. 启动 Telegram 机器人异步后台线程
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # 2. 启动 Flask 网页服务（Render 会自动注入 PORT 环境变量）
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)