"""
Fixtures y configuración para tests automatizados de seguridad y aislamiento multi-tenant.
"""

import pytest
import os
import sys

# Asegurar path del backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base, get_db
import models  # Asegura que todos los modelos ORM se registren en Base.metadata
from main import app
from models.agent import Agent
from models.user_account import UserAccount
from services.auth_service import get_current_user

from sqlalchemy.pool import StaticPool

# Base de datos en memoria para pruebas (StaticPool para que todas las conexiones compartan la misma DB)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
