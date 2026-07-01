import os
import logging
import asyncio
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
    await update.message.reply_text('👋 记账机器人已在云端成功启动！\n\n直接输入 `+10000` 或 `-5000` 记账。\n输入 `/cx` 查询总额。')

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

async def start_bot_async(token):
    """在独立的事件循环中初始化并运行机器人"""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cx", query_total))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bookkeeping))
    
    # 初始化并启动轮询
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logging.info("🤖 Telegram Bot 轮询已成功在后台线程启动！")
    
    # 保持运行
    while True:
        await asyncio.sleep(3600)

def run_bot_thread():
    """后台线程入口：专门用来修复 Python 3.10+ 的无事件循环报错"""
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("❌ 错误: 未找到环境变量 BOT_TOKEN")
        return
    
    # 🔥 核心修复：显式为这个后台线程创建并设置一个新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 使用这个循环运行异步机器人任务
    loop.run_until_complete(start_bot_async(token))

# ---- FLASK 网页伪装逻辑 ----
flask_app = Flask(__name__)

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
        .status { background: #065f46; color: #34d399; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; display: inline-block; margin-top: 1rem; }
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
    # 1. 启动 Telegram 机器人后台线程
    bot_thread = Thread(target=run_bot_thread, name="run_bot")
    bot_thread.daemon = True
    bot_thread.start()

    # 2. 启动 Flask 网页服务
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)
