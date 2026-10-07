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
        messages = db.query(Message).order_by(Message.sent_at.desc()).limit(10).all()
        print("=== LAST 10 MESSAGES ===")
        for m in messages:
            content_safe = m.content.replace('\n', ' ').encode('ascii', 'ignore').decode('ascii')
            print(f"Role: {m.role} | Content: {content_safe[:60]} | Sent: {m.sent_at}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
