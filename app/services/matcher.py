import re
import torch
from transformers import AutoModel, AutoTokenizer
from sqlalchemy import text
from app.schemas import MatchedCandidate, MappingDecision, ReviewStatus
from app.database import SessionLocal

class MDMMatcherService:
    """Синглтон-сервис векторного сопоставления НСИ через pgvector"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MDMMatcherService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        print("[ML Core] Загрузка легковесного RuBERT-tiny2 для векторизации запросов...")
        model_name = "cointegrated/rubert-tiny2"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def _clean_text(self, text: str) -> str:
        """Regex-зачистка скрытых системных шумов"""
        clean = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
        return clean.lower()

    def _get_embeddings(self, texts: list[str]) -> list[float]:
        """Получение pooled эмбеддингов фразы (CLS-токен)"""
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=48,
            return_tensors="pt",
        )
        with torch.no_grad():
            output = self.model(**encoded)
        return output.last_hidden_state[:, 0, :].numpy()[0].tolist()

    def match(self, raw_input: str) -> MappingDecision:
        cleaned = self._clean_text(raw_input)

        if not cleaned or len(cleaned) < 3:
            return MappingDecision(
                input_text=raw_input, status=ReviewStatus.UNRESOLVED
            )

        query_vector = self._get_embeddings([cleaned])
        db = SessionLocal()
        try:
            # Оператор <=> считает косинусное расстояние.
            # Используем безопасный CAST для совместимости с SQLAlchemy
            sql = text("""
                SELECT 
                    id, 
                    standard_name, 
                    1 - (embedding <=> CAST(:vec AS vector)) as cosine_similarity
                FROM golden_records
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT 1;
            """)
            result = db.execute(sql, {"vec": str(query_vector)}).fetchone()
            
            if not result:
                return MappingDecision(input_text=raw_input, status=ReviewStatus.UNRESOLVED)

            golden_id = result[0]
            standard_name = result[1]
            best_score = float(result[2])

        finally:
            db.close()

        if best_score >= 0.85:
            status = ReviewStatus.AUTO_MAPPED
        elif best_score >= 0.55:
            status = ReviewStatus.REQUIRES_HUMAN_REVIEW
        else:
            status = ReviewStatus.UNRESOLVED

        candidate = (
            MatchedCandidate(
                golden_id=golden_id,
                standard_name=standard_name,
                confidence_score=round(best_score, 4),
            )
            if status != ReviewStatus.UNRESOLVED
            else None
        )

        return MappingDecision(
            input_text=raw_input, candidate=candidate, status=status
        )

matcher_service = MDMMatcherService()
