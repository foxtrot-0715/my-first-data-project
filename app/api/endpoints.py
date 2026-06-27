from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import (
    BatchMappingRequest,
    BatchMappingResponse,
    MappingDecision,
)
from app.services.matcher import matcher_service
from app.database import get_db
from app.models.domain import AuditLog

router = APIRouter()


@router.post(
    "/normalize",
    response_model=BatchMappingResponse,
    summary="Нормализация пачки грязной номенклатуры",
)
def normalize_batch(request: BatchMappingRequest, db: Session = Depends(get_db)):
    results = []

    for item in request.items:
        # 1. Спрашиваем ML-движок
        decision = matcher_service.match(item.raw_text)
        results.append(decision)

        # 2. Пишем лог аудита в СУБД
        log_entry = AuditLog(
            raw_input=item.raw_text,
            golden_id=(
                decision.candidate.golden_id if decision.candidate else None
            ),
            standard_name=(
                decision.candidate.standard_name
                if decision.candidate
                else None
            ),
            confidence=(
                decision.candidate.confidence_score
                if decision.candidate
                else None
            ),
            review_status=decision.status.value,
        )
        db.add(log_entry)

    db.commit()
    return BatchMappingResponse(results=results)


@router.get("/stats", summary="Аналитика качества данных (DQ)")
def get_dq_stats(db: Session = Depends(get_db)):
    total = db.query(AuditLog).count()
    if total == 0:
        return {"total_processed": 0, "auto_mapped_percent": 0.0}

    auto_cnt = (
        db.query(AuditLog).filter_by(review_status="AUTO_MAPPED").count()
    )
    review_cnt = (
        db.query(AuditLog)
        .filter_by(review_status="REQUIRES_HUMAN_REVIEW")
        .count()
    )

    return {
        "total_processed": total,
        "auto_mapped": auto_cnt,
        "sent_to_human_review": review_cnt,
        "auto_mapped_percent": round((auto_cnt / total) * 100, 1),
    }