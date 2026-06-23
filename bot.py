import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
ApplicationBuilder,
MessageHandler,
CommandHandler,
ContextTypes,
filters
)
from openpyxl import Workbook

TOKEN = os.getenv("TOKEN")

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

def is_admin(user_id):

```
ADMIN_IDS = [
    123456789
]

return user_id in ADMIN_IDS
```

async def work(update: Update,
context: ContextTypes.DEFAULT_TYPE):

```
uid = update.message.from_user.id

name = (
    update.message.from_user.full_name
)

today = (
    datetime.now()
    .strftime("%Y-%m-%d")
)

cur.execute(
```

"""
SELECT 1
FROM attendance
WHERE user_id=?
AND date=?
""",
(uid, today)
)

```
if cur.fetchone():

    await update.message.reply_text(
    "你已经打过卡了"
    )

    return


cur.execute(
```

"""
INSERT INTO attendance
VALUES(?,?,?)
""",
(uid, name, today)
)

```
db.commit()

await update.message.reply_text(
"打卡成功"
)
```

async def query(update,
context):

```
uid = (
update.message.from_user.id
)

cur.execute(
```

"""
SELECT COUNT(*)
FROM attendance
WHERE user_id=?
""",
(uid,)
)

```
total = (
cur.fetchone()[0]
)

await update.message.reply_text(
```

f"""你的累计上班天数：

{total} 天"""

)

async def admin_query(
update,
context
):

```
uid = (
update.message.from_user.id
)

if not is_admin(uid):

    return


cur.execute(
```

"""
SELECT
name,
COUNT(*)

FROM attendance

GROUP BY name

ORDER BY name
"""
)

```
rows = (
cur.fetchall()
)

msg = (
"全部人员统计\n\n"
)

for n, c in rows:

    msg += (
```

f"{n}：{c}天\n"
)

```
await update.message.reply_text(
msg
)
```

async def excel(
update,
context
):

```
uid = (
update.message.from_user.id
)

if not is_admin(uid):

    return


month = (
```

datetime.now()
.strftime("%Y-%m")
)

```
cur.execute(
```

"""
SELECT
name,
COUNT(*)

FROM attendance

WHERE date
LIKE ?

GROUP BY name

ORDER BY name
""",
(f"{month}%",)
)

```
rows = (
cur.fetchall()
)


wb = Workbook()

ws = wb.active

ws.title = (
"考勤统计"
)


ws.append([
"序号",
"名字",
"打卡天数"
])


index = 1


for n, c in rows:

    ws.append([
        index,
        n,
        c
    ])

    index += 1


filename = (
```

f"{month}考勤.xlsx"
)

```
wb.save(
filename
```

)

```
await update.message.reply_document(
document=open(
filename,
"rb"
)
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
filters.Regex(
"^上班$"
),
work
)
)

app.add_handler(
MessageHandler(
filters.TEXT
&
filters.Regex(
"^查询$"
),
query
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
excel
)
)

print(
"机器人启动成功"
)

app.run_polling()
