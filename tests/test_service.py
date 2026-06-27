import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.matcher import matcher_service

client = TestClient(app)


def test_health_check():
    """Проверка доступности API"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_regex_deep_clean_bugfix():
    """Проверка зачистки скрытого системного шума 1С (\xa0)"""
    dirty_str = "Кабель ВВГ  \xa0 3х1.5 плоский  "
    cleaned = matcher_service._clean_text(dirty_str)
    assert "\xa0" not in cleaned
    assert cleaned == "кабель ввг 3х1.5 плоский"


def test_normalize_endpoint_valid_matching():
    """Проверка успешной проекции на L2-сферу и сопоставления с эталоном"""
    payload = {"items": [{"raw_text": "Подшипник радиальный 6204-2rs \xa0"}]}
    response = client.post("/api/v1/normalize", json=payload)
    assert response.status_code == 200

    data = response.json()["results"][0]
    assert data["status"] in ["AUTO_MAPPED", "REQUIRES_HUMAN_REVIEW"]
    assert data["candidate"]["golden_id"] == 103


def test_normalize_endpoint_garbage_input():
    """Проверка отсечения аномалий"""
    payload = {"items": [{"raw_text": "ъуъ фхтагн"}]}
    response = client.post("/api/v1/normalize", json=payload)
    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "UNRESOLVED"