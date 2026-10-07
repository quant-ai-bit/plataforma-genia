from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.conversation import Message, Conversation
import sys

DATABASE_URL = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

def check():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        conv = db.query(Conversation).filter(Conversation.contact_phone == "PAYLOAD_DEBUG").first()
        if not conv:
            print("[DEBUG] No PAYLOAD_DEBUG conversation found yet.")
            return
            
        messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.sent_at.desc()).limit(5).all()
        print(f"=== FOUND {len(messages)} DEBUG PAYLOADS ===")
        for m in messages:
            print(f"Sent At: {m.sent_at}")
            print(m.content)
            print("-" * 80)
    finally:
        db.close()

if __name__ == "__main__":
    check()
