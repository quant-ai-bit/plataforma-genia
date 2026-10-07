from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.agent import Agent
from sqlalchemy.orm.attributes import flag_modified

engine = create_engine(
    "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres",
    connect_args={"sslmode": "require", "connect_timeout": 5, "prepare_threshold": None}
)
Session = sessionmaker(bind=engine)
db = Session()

agents = db.query(Agent).all()
for a in agents:
    if a.custom_fields:
        new_custom = []
        for f in a.custom_fields:
            if isinstance(f, dict):
                k = f.get("key") or f.get("name") or "custom_field"
                lbl = f.get("label") or f.get("description") or k
                new_custom.append({
                    "key": k,
                    "label": lbl,
                    "type": f.get("type", "text"),
                    "required": f.get("required", False)
                })
        a.custom_fields = new_custom
        flag_modified(a, "custom_fields")

db.commit()
print("Successfully normalized custom_fields in Supabase DB!")
