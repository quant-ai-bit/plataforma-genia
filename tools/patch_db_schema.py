import sqlite3
import os

def patch_db(db_path):
    if not os.path.exists(db_path):
        print(f"Db path {db_path} not found.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check/Add tenant_id in agents
    cursor.execute("PRAGMA table_info(agents)")
    columns_agents = [c[1] for c in cursor.fetchall()]
    if "tenant_id" not in columns_agents:
        print(f"Adding tenant_id to agents in {db_path}")
        try:
            cursor.execute("ALTER TABLE agents ADD COLUMN tenant_id VARCHAR")
            conn.commit()
        except Exception as e:
            print(f"Error adding tenant_id to agents: {e}")
            
    # 2. Check/Add enabled_mcp_tools in agents
    if "enabled_mcp_tools" not in columns_agents:
        print(f"Adding enabled_mcp_tools to agents in {db_path}")
        try:
            cursor.execute("ALTER TABLE agents ADD COLUMN enabled_mcp_tools TEXT")
            conn.commit()
        except Exception as e:
            print(f"Error adding enabled_mcp_tools to agents: {e}")

    # 3. Check/Add whatsapp_qr_code in agents
    if "whatsapp_qr_code" not in columns_agents:
        print(f"Adding whatsapp_qr_code to agents in {db_path}")
        try:
            cursor.execute("ALTER TABLE agents ADD COLUMN whatsapp_qr_code TEXT")
            conn.commit()
        except Exception as e:
            print(f"Error adding whatsapp_qr_code to agents: {e}")
            
    # 4. Check/Add tenant_id in knowledge_documents
    cursor.execute("PRAGMA table_info(knowledge_documents)")
    columns = [c[1] for c in cursor.fetchall()]
    if "tenant_id" not in columns:
        print(f"Adding tenant_id to knowledge_documents in {db_path}")
        try:
            cursor.execute("ALTER TABLE knowledge_documents ADD COLUMN tenant_id VARCHAR")
            conn.commit()
        except Exception as e:
            print(f"Error adding tenant_id: {e}")
            
    # 5. Check/Add tenant_id in knowledge_chunks
    cursor.execute("PRAGMA table_info(knowledge_chunks)")
    columns_chunks = [c[1] for c in cursor.fetchall()]
    if "tenant_id" not in columns_chunks:
        print(f"Adding tenant_id to knowledge_chunks in {db_path}")
        try:
            cursor.execute("ALTER TABLE knowledge_chunks ADD COLUMN tenant_id VARCHAR")
            conn.commit()
        except Exception as e:
            print(f"Error adding tenant_id: {e}")
            
    conn.close()

if __name__ == "__main__":
    patch_db("backend/data/genia.db")
    patch_db("data/genia.db")
    print("Done patching schemas.")
