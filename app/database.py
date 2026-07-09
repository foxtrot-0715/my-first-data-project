import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.domain import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mdm_storage.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Функция автоматической генерации таблиц при старте сервиса"""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Гасим ошибку состояния гонки (Race Condition), 
        # когда 4 воркера одновременно пытаются создать одну и ту же таблицу
        pass

def get_db():
    """Генератор сессий базы данных для FastAPI Dependency Injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()