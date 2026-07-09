from datetime import datetime
from typing import Optional  # <-- ТА САМАЯ НЕДОСТАЮЩАЯ СТРОЧКА
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Базовый класс SQLAlchemy 2.0"""

    pass


class AuditLog(Base):
    """Таблица постоянного хранения истории матчинга (СУБД)"""

    __tablename__ = "nomenclature_audit_log"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    raw_input: Mapped[str] = mapped_column(
        String, index=True, comment="Входящая грязная строка"
    )
    golden_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="ID выбранного эталона"
    )
    standard_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="Имя эталона"
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Скор уверенности модели"
    )
    review_status: Mapped[str] = mapped_column(
        String, index=True, comment="Вердикт: AUTO_MAPPED / REQUIRES_REVIEW"
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, input='{self.raw_input[:15]}...', status='{self.review_status}')>"

class GoldenRecord(Base):
    """Эталонный справочник номенклатуры (Мастер-каталог)"""
    __tablename__ = "golden_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    standard_name: Mapped[str] = mapped_column(String, index=True, comment="Чистое наименование")