"""
Script de migración para crear la tabla user_accounts en la base de datos local y remota (Supabase).
"""

import os
import sys
from sqlalchemy import create_engine, text

# Añadir directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
import models

def migrate():
    print("Iniciando creación/verificación de tabla user_accounts...")
    
    # 1. Usar SQLAlchemy Base metadata para crear tablas pendientes
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Tablas creadas/verificadas en la base de datos activa:", engine.url)
    except Exception as e:
        print("[ERROR] Error en create_all:", e)

    # 2. Si la base de datos remota de Supabase está configurada en .env.production, aplicarla también
    prod_db_url = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"
    try:
        prod_engine = create_engine(prod_db_url, connect_args={"connect_timeout": 10})
        Base.metadata.create_all(bind=prod_engine)
        print("[OK] Tablas creadas/verificadas en Supabase PostgreSQL producción.")
    except Exception as e:
        print("[WARNING] No se pudo conectar a la BD remota de producción:", e)

if __name__ == "__main__":
    migrate()
