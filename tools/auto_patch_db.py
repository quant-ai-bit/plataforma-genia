import os
import sys
import sqlite3

# Allow importing from backend
sys.path.insert(0, os.path.abspath("backend"))

from database import Base, engine
import models.agent
import models.conversation
import models.knowledge
import models.lead

def auto_patch_sqlite(db_path):
    if not os.path.exists(db_path):
        print(f"Db path {db_path} not found.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Iterate over all mapped tables in SQLAlchemy Base
    for table_name, table in Base.metadata.tables.items():
        # Check if table exists in SQLite
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            print(f"Table '{table_name}' does not exist in SQLite database. Skipping.")
            continue
            
        # Get existing columns in SQLite table
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        # Iterate over columns in SQLAlchemy definition
        for col in table.columns:
            if col.name not in existing_cols:
                col_type = "TEXT"
                # Map some basic types
                from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON
                if isinstance(col.type, Integer):
                    col_type = "INTEGER"
                elif isinstance(col.type, Float):
                    col_type = "REAL"
                elif isinstance(col.type, Boolean):
                    col_type = "BOOLEAN"
                elif isinstance(col.type, DateTime):
                    col_type = "DATETIME"
                    
                print(f"Adding column '{col.name}' ({col_type}) to table '{table_name}' in {db_path}...")
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}")
                    conn.commit()
                except Exception as e:
                    print(f"Error adding column '{col.name}': {e}")
                    
    conn.close()

if __name__ == "__main__":
    auto_patch_sqlite("backend/data/genia.db")
    auto_patch_sqlite("data/genia.db")
    print("Done auto-patching SQLite schemas.")
