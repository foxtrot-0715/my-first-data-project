from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReviewStatus(str, Enum):
    """Бизнес-статусы разбора номенклатуры"""

    AUTO_MAPPED = "AUTO_MAPPED"  # Уверенность >= 0.95 (авто-мерж)
    REQUIRES_HUMAN_REVIEW = (
        "REQUIRES_HUMAN_REVIEW"  # Уверенность 0.70 - 0.94 (на ручной аппрув)
    )
    UNRESOLVED = "UNRESOLVED"  # Уверенность < 0.70 (мусор / аномалия)


class NomenclatureInput(BaseModel):
    """Контракт входящего запроса от ERP-системы"""

    raw_text: str = Field(
        ...,
        examples=["Кабель ВВГнг-ls 3х1.5 \xa0"],
        description="Сырая строка номенклатуры из накладной",
    )


class MatchedCandidate(BaseModel):
    """Контракт найденного эталона (Golden Record)"""

    golden_id: int = Field(..., description="ID эталонной записи в НСИ")
    standard_name: str = Field(
        ..., description="Нормализованное эталонное наименование"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Косинусная схожесть на L2-сфере (0..1)",
    )

    # ConfigDict(from_attributes=True) — это современная замена старого orm_mode=True из Pydantic v1
    model_config = ConfigDict(from_attributes=True)


class MappingDecision(BaseModel):
    """Итоговый ответ бэкенда по одной позиции"""

    input_text: str = Field(..., description="Исходный грязный текст")
    candidate: Optional[MatchedCandidate] = Field(
        None, description="Найденный кандидат (если есть)"
    )
    status: ReviewStatus = Field(..., description="Вердикт системы")

    model_config = ConfigDict(from_attributes=True)


class BatchMappingRequest(BaseModel):
    """Пачка грязных строк для пакетной обработки"""

    items: List[NomenclatureInput]


class BatchMappingResponse(BaseModel):
    """Ответ на пакетную обработку"""

    results: List[MappingDecision]