import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = "8924411075:AAEpy5a0IlVAGJCH2CtOMRERO8eGCFMEsCE"

ADMIN_ID = 123456789

db = sqlite3.connect(
    "work.db",
    check_same_thread=False
)

cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS checkin(
id INTEGER PRIMARY KEY,
user_id INTEGER,
name TEXT,
date TEXT
)
""")

db.commit()


async def checkin(update: Update, context):

    user = update.message.from_user

    uid = user.id

    name = user.first_name

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    cur.execute(
        """
        SELECT *
        FROM checkin
        WHERE user_id=?
        AND date=?
        """,
        (uid, today),
    )

    if cur.fetchone():

        await update.message.reply_text(
            "今天已经打过卡"
        )

        return

    cur.execute(
        """
        INSERT INTO checkin
        (user_id,name,date)
        VALUES(?,?,?)
        """,
        (uid, name, today),
    )

    db.commit()

    await update.message.reply_text(
        f"打卡成功\n日期：{today}"
    )


async def cx(update, context):

    uid = update.message.from_user.id

    if uid == ADMIN_ID:

        cur.execute("""
        SELECT name,
        COUNT(*)
        FROM checkin
        GROUP BY user_id
        """)

        rows = cur.fetchall()

        txt = "全部统计\n\n"

        for r in rows:

            txt += (
                f"{r[0]}："
                f"{r[1]}天\n"
            )

        await update.message.reply_text(
            txt
        )

    else:

        cur.execute(
            """
            SELECT COUNT(*)
            FROM checkin
            WHERE user_id=?
            """,
            (uid,),
        )

        days = cur.fetchone()[0]

        await update.message.reply_text(
            f"你累计上班 {days} 天"
        )


app = (
ApplicationBuilder()
.token(TOKEN)
.build()
)

app.add_handler(
CommandHandler(
"cx",
cx
)
)

app.add_handler(
MessageHandler(
filters.TEXT
&
filters.Regex("^上班$"),
checkin
)
)

app.run_polling()
