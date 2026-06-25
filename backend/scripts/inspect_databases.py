import sqlite3
import sys

def inspect_db(path, out):
    out.write(f"\n=================== INSPECTING: {path} ===================\n")
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        out.write(f"Table '{table}': {count} rows\n")
        if count > 0 and table in ['agents', 'tenant', 'conversations', 'leads', 'api_key']:
            cursor.execute(f"PRAGMA table_info({table});")
            cols = [c[1] for c in cursor.fetchall()]
            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
            rows = cursor.fetchall()
            out.write(f"  Sample rows in '{table}':\n")
            for r in rows:
                out.write(f"    {dict(zip(cols, r))}\n")
    conn.close()

if __name__ == '__main__':
    with open('backend/scripts/inspect_result.txt', 'w', encoding='utf-8') as out:
        inspect_db('backend/data/genia.db', out)
        inspect_db('backend/data/genia.db.bak', out)
