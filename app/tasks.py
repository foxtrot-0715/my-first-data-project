from app.celery_app import celery_task_app
from app.services.matcher import matcher_service
from app.database import SessionLocal
from app.models.domain import AuditLog

@celery_task_app.task(bind=True)
def process_batch_task(self, items_texts: list[str]):
    """
    Фоновая задача Celery. Забирает тексты, прогоняет через RuBERT и пишет в базу.
    """
    db = SessionLocal()
    results = []
    
    try:
        for text in items_texts:
            # 1. Спрашиваем ML-движок
            decision = matcher_service.match(text)
            
            # Сериализуем объект в словарь (Celery работает с JSON)
            results.append({
                "raw_text": text,
                "golden_id": decision.candidate.golden_id if decision.candidate else None,
                "standard_name": decision.candidate.standard_name if decision.candidate else None,
                "confidence_score": decision.candidate.confidence_score if decision.candidate else None,
                "status": decision.status.value
            })

            # 2. Пишем лог аудита в СУБД
            log_entry = AuditLog(
                raw_input=text,
                golden_id=decision.candidate.golden_id if decision.candidate else None,
                standard_name=decision.candidate.standard_name if decision.candidate else None,
                confidence=decision.candidate.confidence_score if decision.candidate else None,
                review_status=decision.status.value,
            )
            db.add(log_entry)

        db.commit()
        return {"status": "COMPLETED", "results": results}
        
    except Exception as e:
        db.rollback()
        return {"status": "FAILED", "error": str(e)}
    finally:
        db.close()