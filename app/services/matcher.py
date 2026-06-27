import re
import numpy as np
from sklearn.preprocessing import normalize
import torch
from transformers import AutoModel, AutoTokenizer
from app.schemas import MatchedCandidate, MappingDecision, ReviewStatus


class MDMMatcherService:
    """Синглтон-сервис векторного сопоставления НСИ на единичной гиперсфере"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MDMMatcherService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        print(
            "[ML Core] Загрузка легковесного RuBERT-tiny2 в память воркера..."
        )
        model_name = "cointegrated/rubert-tiny2"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

        # Наша эталонная база НСИ (Golden Record Catalog)
        self.master_catalog = {
            101: "Кабель силовой ВВГнг(А)-LS 3х1.5 плоский",
            102: "Кабель силовой ВВГнг(А)-LS 3х2.5 плоский",
            103: "Подшипник шариковый радиальный 6204-2RS (20х47х14)",
            104: "Подшипник качения роликовый 7204 (30204)",
            105: "Труба гофрированная ПВХ д.20 мм с зондом",
        }

        # Предрасчет L2-нормализованных векторов Мастер-каталога при старте сервиса!
        print("[ML Core] Проекция Мастер-каталога на единичную L2-сферу...")
        master_texts = list(self.master_catalog.values())
        raw_embs = self._get_embeddings(master_texts)
        self.master_vectors = normalize(raw_embs, norm="l2")  # Матрица (5, 312)

    def _clean_text(self, text: str) -> str:
        """Та самая Regex-зачистка скрытых системных шумов"""
        # Сносим \xa0, двойные пробелы и приводим к нижнему регистру
        clean = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
        return clean.lower()

    def _get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Получение pooled эмбеддингов фразы (CLS-токен)"""
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=48,  # Оптимизация матричных умножений из нашего EDA!
            return_tensors="pt",
        )
        with torch.no_grad():
            output = self.model(**encoded)
        return output.last_hidden_state[:, 0, :].numpy()

    def match(self, raw_input: str) -> MappingDecision:
        cleaned = self._clean_text(raw_input)

        if not cleaned or len(cleaned) < 3:
            return MappingDecision(
                input_text=raw_input, status=ReviewStatus.UNRESOLVED
            )

        # Векторизуем грязный запрос и проецируем на L2-сферу
        query_emb = self._get_embeddings([cleaned])
        query_vector = normalize(query_emb, norm="l2")  # Вектор (1, 312)

        # Матричное умножение (Dot Product на единичной сфере = Косинусная близость!)
        similarities = np.dot(self.master_vectors, query_vector.T).flatten()

        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        golden_id = list(self.master_catalog.keys())[best_idx]
        standard_name = self.master_catalog[golden_id]

        # Бизнес-логика маршрутизации данных (Пороги уверенности)
        if best_score >= 0.85:  # Уверенное совпадение -> Авто-мерж
            status = ReviewStatus.AUTO_MAPPED
        elif best_score >= 0.55:  # Сомнение -> Отправка в UI асессору
            status = ReviewStatus.REQUIRES_HUMAN_REVIEW
        else:  # Мусор / Аномалия
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