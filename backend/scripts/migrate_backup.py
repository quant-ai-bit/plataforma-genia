import sqlite3

def get_columns(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table});")
    return [c[1] for c in cursor.fetchall()]

def migrate_table(table):
    print(f"Migrating table: {table}")
    conn_bak = sqlite3.connect('backend/data/genia.db.bak')
    conn_new = sqlite3.connect('backend/data/genia.db')
    
    cols_bak = get_columns(conn_bak, table)
    cols_new = get_columns(conn_new, table)
    
    print(f"  Bak columns: {cols_bak}")
    print(f"  New columns: {cols_new}")
    
    # Find intersection of columns
    common_cols = [c for c in cols_bak if c in cols_new]
    print(f"  Common columns: {common_cols}")
    
    cursor_bak = conn_bak.cursor()
    cursor_bak.execute(f"SELECT {', '.join(common_cols)} FROM {table}")
    rows = cursor_bak.fetchall()
    print(f"  Found {len(rows)} rows in bak to migrate.")
    
    cursor_new = conn_new.cursor()
    inserted = 0
    for row in rows:
        # Check if record already exists by id (assuming id is first column or we have id)
        has_id = 'id' in common_cols
        if has_id:
            id_idx = common_cols.index('id')
            row_id = row[id_idx]
            cursor_new.execute(f"SELECT COUNT(*) FROM {table} WHERE id = ?", (row_id,))
            exists = cursor_new.fetchone()[0] > 0
            if exists:
                print(f"  Row with id {row_id} already exists in new database. Skipping.")
                continue
        
        placeholders = ', '.join(['?'] * len(common_cols))
        query = f"INSERT INTO {table} ({', '.join(common_cols)}) VALUES ({placeholders})"
        cursor_new.execute(query, row)
        inserted += 1
        
    conn_new.commit()
    print(f"  Successfully inserted {inserted} rows.")
    conn_bak.close()
    conn_new.close()

if __name__ == '__main__':
    migrate_table('agents')
    migrate_table('knowledge_documents')
