import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.domain import Base

# По умолчанию разворачиваем локальную SQLite в корне проекта
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mdm_storage.db")

# connect_args={"check_same_thread": False} — ЖИЗНЕННО ВАЖНЫЙ костыль для SQLite,
# чтобы многопоточный FastAPI не падал с ошибкой "object created in another thread"
engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Функция автоматической генерации таблиц при старте сервиса"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Генератор сессий базы данных для FastAPI Dependency Injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()