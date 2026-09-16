"""
Configuración de base de datos SQLAlchemy para PLATAFORMA GENIA.

Usa SQLite por defecto (archivo en ./data/genia.db).
Migrable a PostgreSQL cambiando DATABASE_URL sin modificar código.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# Crear directorio de datos si no existe
try:
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
except Exception as e:
    # En entornos de solo lectura (como Vercel producción), ignoramos errores de filesystem
    # ya que se utiliza Supabase Storage y pgvector en su lugar.
    import logging
    logging.getLogger(__name__).warning(
        "No se pudieron crear los directorios locales (esperado en entornos Serverless de solo lectura): %s",
        str(e)
    )

from sqlalchemy.pool import NullPool

is_sqlite = "sqlite" in settings.effective_database_url
is_vercel = os.getenv("VERCEL") == "1" or os.getenv("ENVIRONMENT") == "production"

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["connect_args"] = {
        "prepare_threshold": None,
        "connect_timeout": 10,
    }
    if is_vercel:
        # En Vercel Serverless, NullPool previene que las lambdas agoten conexiones en Supabase o se cuelguen
        engine_kwargs.update(
            poolclass=NullPool,
            pool_pre_ping=True,
        )
    else:
        engine_kwargs.update(
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=300,
        )

engine = create_engine(
    settings.effective_database_url,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependencia de FastAPI para obtener una sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Inicializa la base de datos aplicando todas las migraciones de Alembic."""
    if os.getenv("VERCEL") == "1":
        # En Vercel Serverless no ejecutamos Alembic DDL en cada invocación HTTP para evitar timeouts
        return

    from alembic.config import Config
    from alembic import command

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ini_path = os.path.join(base_dir, "alembic.ini")
        
        if os.path.exists(ini_path):
            alembic_cfg = Config(ini_path)
            alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
            command.upgrade(alembic_cfg, "head")
            print("[OK] Base de datos inicializada y migrada correctamente con Alembic.")
        else:
            raise FileNotFoundError(f"No se encontró alembic.ini en {ini_path}")
    except Exception as e:
        print(f"[WARNING] Falló la migración automática con Alembic: {e}")
        print("Intentando inicialización básica con create_all...")
        import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        print("[OK] Base de datos inicializada con create_all.")


