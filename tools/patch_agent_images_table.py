"""
Script para alterar la tabla agent_images en Supabase PostgreSQL y SQLite local
cambiando el tipo de datos de filename, description y url a TEXT.
"""

import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import logging
from sqlalchemy import create_engine, text
from tools.create_agent_juan import SUPABASE_DB_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def patch_supabase_agent_images():
    logger.info("Modificando la tabla agent_images en Supabase PostgreSQL...")
    engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE agent_images ALTER COLUMN filename TYPE TEXT;"))
            conn.execute(text("ALTER TABLE agent_images ALTER COLUMN description TYPE TEXT;"))
            conn.execute(text("ALTER TABLE agent_images ALTER COLUMN url TYPE TEXT;"))
            conn.commit()
            logger.info("✅ Columnas agent_images (filename, description, url) convertidas a TEXT exitosamente en Supabase PostgreSQL.")
        except Exception as e:
            logger.error("❌ Error alterando columnas en Supabase: %s", e)

if __name__ == "__main__":
    patch_supabase_agent_images()
