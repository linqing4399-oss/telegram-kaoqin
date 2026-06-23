import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
ApplicationBuilder,
CommandHandler,
MessageHandler,
ContextTypes,
filters,
)
from openpyxl import Workbook

TOKEN = os.getenv("TOKEN")

ADMIN_IDS = [
lq07168
]

db = sqlite3.connect(
"attendance.db",
check_same_thread=False
)

cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS attendance(
user_id INTEGER,
name TEXT,
date TEXT
)
""")

db.commit()

def is_admin(uid):
return uid in ADMIN_IDS

def get_month():
return datetime.now().strftime("%Y-%m")

def get_today():
return datetime.now().strftime("%Y-%m-%d")

async def checkin(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

```
uid = update.message.from_user.id

name = (
    update.message.from_user.full_name
)

today = get_today()

cur.execute(
    """
    SELECT 1
    FROM attendance
    WHERE user_id=?
    AND date=?
    """,
    (
        uid,
        today
    )
)

exists = cur.fetchone()

if exists:

    await update.message.reply_text(
        "你已经打过卡了"
    )

    return

cur.execute(
    """
    INSERT INTO attendance
    VALUES(?,?,?)
    """,
    (
        uid,
        name,
        today
    )
)

db.commit()

await update.message.reply_text(
    "打卡成功"
)
```

async def month_query(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

```
uid = update.message.from_user.id

month = get_month()

cur.execute(
    """
    SELECT COUNT(*)
    FROM attendance
    WHERE user_id=?
    AND date LIKE ?
    """,
    (
        uid,
        f"{month}%"
    )
)

days = cur.fetchone()[0]

await update.message.reply_text(
    f"你本月已上班：\n{days} 天"
)
```

async def total_query(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

```
uid = update.message.from_user.id

cur.execute(
    """
    SELECT COUNT(*)
    FROM attendance
    WHERE user_id=?
    """,
    (
        uid,
    )
)

total = cur.fetchone()[0]

await update.message.reply_text(
    f"历史累计：\n{total} 天"
)
```

async def admin_query(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

```
uid = update.message.from_user.id

if not is_admin(uid):

    return

month = get_month()

cur.execute(
    """
    SELECT
    name,
    COUNT(*)

    FROM attendance

    WHERE date LIKE ?

    GROUP BY name

    ORDER BY name ASC
    """,
    (
        f"{month}%",
    )
)

rows = cur.fetchall()

if not rows:

    await update.message.reply_text(
        "暂无数据"
    )

    return

msg = f"{month} 上班统计\n\n"

for name, days in rows:

    msg += (
        f"{name}：{days}天\n"
    )

await update.message.reply_text(
    msg
)
```

async def export_excel(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

```
uid = update.message.from_user.id

if not is_admin(uid):

    return

month = get_month()

cur.execute(
    """
    SELECT
    name,
    COUNT(*)

    FROM attendance

    WHERE date LIKE ?

    GROUP BY name

    ORDER BY name ASC
    """,
    (
        f"{month}%",
    )
)

rows = cur.fetchall()

wb = Workbook()

ws = wb.active

ws.title = "考勤统计"

ws.append([
    "序号",
    "名字",
    "打卡天数"
])

for i, row in enumerate(
    rows,
    start=1
):

    ws.append([
        i,
        row[0],
        row[1]
    ])

filename = (
    f"{month}_考勤.xlsx"
)

wb.save(
    filename
)

with open(
    filename,
    "rb"
) as file:

    await update.message.reply_document(
        file
    )
```

app = (
ApplicationBuilder()
.token(TOKEN)
.build()
)

app.add_handler(
MessageHandler(
filters.TEXT
&
filters.Regex("^上班$"),
checkin
)
)

app.add_handler(
MessageHandler(
filters.TEXT
&
filters.Regex("^查询$"),
month_query
)
)

app.add_handler(
MessageHandler(
filters.TEXT
&
filters.Regex("^累计$"),
total_query
)
)

app.add_handler(
CommandHandler(
"cx",
admin_query
)
)

app.add_handler(
CommandHandler(
"excel",
export_excel
)
)

print(
"机器人启动成功"
)

app.run_polling()
