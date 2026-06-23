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

ADMIN_IDS = [
lq07168
]

def is_admin(uid):
    return uid in ADMIN_IDS

def current_month():
    return datetime.now().strftime(
"%Y-%m"
)

async def work(
update: Update,
context
):

```
uid = (
update.message.from_user.id
)

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

async def month_query(
update,
context
):

```
uid = (
update.message.from_user.id
)

month = (
current_month()
)

cur.execute(
```

"""
SELECT COUNT(*)

FROM attendance

WHERE user_id=?
AND date
LIKE ?
""",

(
uid,
f"{month}%"
)
)

```
days = (
cur.fetchone()[0]
)

await update.message.reply_text(
```

f"""你本月已上班：

{days} 天"""

)

async def total_query(
update,
context
):

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

f"""历史累计：

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


month = (
current_month()
)

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

(
f"{month}%",
)
)

```
rows = (
cur.fetchall()
)


msg = (
```

f"{month} 上班统计\n\n"
)

```
for n, d in rows:

    msg += (
```

f"{n}：{d}天\n"
)

```
await update.message.reply_text(
msg
)
```

async def export_excel(
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
current_month()
)

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

(
f"{month}%",
)
)

```
rows = (
cur.fetchall()
)


wb = Workbook()

ws = wb.active

ws.title = (
month
)


ws.append([
"序号",
"名字",
"打卡天数"
])


i = 1


for n, d in rows:

    ws.append([
        i,
        n,
        d
    ])

    i += 1


file = (
```

f"{month}_考勤.xlsx"
)

```
wb.save(
file
)


await update.message.reply_document(
open(
file,
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
r"^上班$"
),
work
)
)

app.add_handler(
MessageHandler(
filters.TEXT
&
filters.Regex(
r"^查询$"
),
month_query
)
)

app.add_handler(
MessageHandler(
filters.TEXT
&
filters.Regex(
r"^累计$"
),
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
