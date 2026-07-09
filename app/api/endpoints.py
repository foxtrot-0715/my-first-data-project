from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.celery_app import celery_task_app
from app.schemas import BatchMappingRequest
from app.database import get_db
from app.models.domain import AuditLog

# ВАЖНО: Мы удалили импорт app.tasks! Бэкенд больше не грузит PyTorch в память!

router = APIRouter()

@router.post(
    "/normalize/async",
    summary="Асинхронная нормализация пачки грязной номенклатуры (через очередь)",
)
def normalize_batch_async(request: BatchMappingRequest):
    items_texts = [item.raw_text for item in request.items]
    
    # Отправляем задачу брокеру просто по текстовому имени. 
    # ML-модель для этого загружать не нужно!
    task = celery_task_app.send_task('app.tasks.process_batch_task', args=[items_texts])
    
    return {"task_id": task.id, "status": "PROCESSING"}


@router.get(
    "/normalize/status/{task_id}", 
    summary="Получение результатов асинхронной нормализации"
)
def get_task_status(task_id: str):
    task_result = celery_task_app.AsyncResult(task_id)
    
    if task_result.state == 'PENDING' or task_result.state == 'STARTED':
        return {"task_id": task_id, "status": "PROCESSING"}
    elif task_result.state == 'SUCCESS':
        return task_result.result 
    else:
        return {"task_id": task_id, "status": "FAILED", "error": str(task_result.info)}


@router.get("/stats", summary="Аналитика качества данных (DQ)")
def get_dq_stats(db: Session = Depends(get_db)):
    total = db.query(AuditLog).count()
    if total == 0:
        return {"total_processed": 0, "auto_mapped_percent": 0.0}

    auto_cnt = db.query(AuditLog).filter_by(review_status="AUTO_MAPPED").count()
    review_cnt = db.query(AuditLog).filter_by(review_status="REQUIRES_HUMAN_REVIEW").count()

    return {
        "total_processed": total,
        "auto_mapped": auto_cnt,
        "sent_to_human_review": review_cnt,
        "auto_mapped_percent": round((auto_cnt / total) * 100, 1),
    }