import psycopg

conn = psycopg.connect('postgresql://postgres.your-tenant-id:124c92be406d143842e01a4c0c09fb1c@136.248.126.192:5432/postgres')
cur = conn.cursor()

with open("data/backups/restore_data.sql", "r", encoding="utf-8") as f:
    sql = f.read()

cur.execute(sql)
conn.commit()

print("Executed restore_data.sql successfully!")

for tbl in ["users", "printers", "filaments", "projects", "plates", "bom_items"]:
    cur.execute(f'SELECT count(*) FROM "3dprintcalc".{tbl}')
    cnt = cur.fetchone()[0]
    print(f"Table '3dprintcalc.{tbl}': {cnt} rows")

conn.close()
