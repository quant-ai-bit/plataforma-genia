import os
import sys

# Allow importing from backend
sys.path.insert(0, os.path.abspath("backend"))

# Load env variables from backend/.env if it exists
backend_env_path = "backend/.env"
if os.path.exists(backend_env_path):
    print(f"Loading env from {backend_env_path}")
    with open(backend_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val

# Load env variables from .env.development.local if it exists
env_path = ".env.development.local"
if os.path.exists(env_path):
    print(f"Loading env from {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val

# Set environment to development to bypass JWT validation etc.
os.environ["ENVIRONMENT"] = "development"

# Remove GOOGLE_APPLICATION_CREDENTIALS to prevent 403 scope issues in local environment
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

from database import SessionLocal
from services.knowledge_service import delete_document, process_and_index_document

AGENT_ID = "547c07f714394e399c504d4bb3da37ac"
DOC_ID = "39fcc6c1509e4e59835da8e2c20ed2a4"

def main():
    db = SessionLocal()
    try:
        # Read new KB file content
        kb_file_path = "tools/BC_Social.txt"
        if not os.path.exists(kb_file_path):
            print(f"Error: {kb_file_path} not found")
            return
            
        with open(kb_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 1. Delete old document and its chunks/embeddings
        print(f"Deleting old document {DOC_ID}...")
        deleted = delete_document(db, DOC_ID)
        print(f"Deleted old document status: {deleted}")
        
        # 2. Add new document and re-embed/re-index it
        print("Indexing new document...")
        new_doc = process_and_index_document(
            db=db,
            agent_id=AGENT_ID,
            filename="BC Social.txt",
            content_type="text/plain",
            file_bytes=content.encode("utf-8")
        )
        # Force the ID to match DOC_ID for consistency/retrocompatibility
        new_doc.id = DOC_ID
        db.commit()
        print(f"Successfully processed and indexed new document. ID set back to: {DOC_ID}")
        
    except Exception as e:
        db.rollback()
        print(f"Error during update: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
