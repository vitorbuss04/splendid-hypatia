import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/dev.db")
BACKUP_DIR = Path("data/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_db_path = BACKUP_DIR / f"dev_backup_{timestamp}.db"
backup_json_path = BACKUP_DIR / f"dev_backup_{timestamp}.json"

# 1. Copy SQLite db file
shutil.copy2(DB_PATH, backup_db_path)
print(f"Copied {DB_PATH} to {backup_db_path}")

# 2. Dump all tables and rows to JSON
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = [row['name'] for row in cursor.fetchall()]

dump = {}
for t in tables:
    cursor.execute(f"PRAGMA table_info({t})")
    columns = [dict(c) for c in cursor.fetchall()]
    
    cursor.execute(f"SELECT * FROM {t}")
    rows = [dict(r) for r in cursor.fetchall()]
    
    dump[t] = {
        "columns": columns,
        "count": len(rows),
        "rows": rows
    }
    print(f"Table '{t}': {len(rows)} rows")

with open(backup_json_path, "w", encoding="utf-8") as f:
    json.dump(dump, f, indent=2, default=str, ensure_ascii=False)

print(f"Saved JSON dump to {backup_json_path}")
conn.close()
