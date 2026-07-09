import streamlit as st
import requests
import os
import time

# Если переменная проброшена из Docker — берем её. Если запускаем руками — берем localhost
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="MDM AI Lakehouse | НСИ", page_icon="🗂️", layout="wide"
)

st.title("🗂️ MDM AI Lakehouse: Контур Data Quality")
st.caption(
    "Интеллектуальная нормализация и дедупликация мастер-данных на базе RuBERT-tiny2 (L2-Space)"
)

# --- БОКОВАЯ ПАНЕЛЬ: Статистика из СУБД ---
with st.sidebar:
    st.header("📊 Телеметрия СУБД")
    try:
        stats = requests.get(f"{API_BASE_URL}/stats").json()
        st.metric(
            "Всего обработано позиций", stats.get("total_processed", 0)
        )
        st.metric(
            "Доля автоматического мержа",
            f"{stats.get('auto_mapped_percent', 0.0)}%",
            help="Записи с Confidence >= 85%",
        )
        st.metric(
            "Отправлено асессору (UI)", stats.get("sent_to_human_review", 0)
        )
    except Exception:
        st.warning(
            "⚠️ Бэкенд FastAPI недоступен. Проверьте машинное отделение!"
        )

# --- ОСНОВНОЙ ЭКРАН: Интерактивный полигон ---
st.subheader("⚡ Полигон нормализации сырых строк")

# Текстовое поле с грязным примером по умолчанию
raw_input = st.text_area(
    "Введите наименование товара из накладной (1С / ТТН):",
    value="Подшипник качения роликовый 7204  \xa0 (30204)  ",
    height=100,
)

if st.button("🚀 Нормализовать запись", type="primary"):
    payload = {"items": [{"raw_text": raw_input}]}

    try:
        # 1. Отправляем задачу в очередь Redis
        response = requests.post(
            f"{API_BASE_URL}/normalize/async", json=payload
        )

        if response.status_code == 200:
            task_id = response.json().get("task_id")

            # 2. Запускаем режим ожидания (Polling)
            with st.spinner("Отправка в очередь. Инференс RuBERT-tiny2..."):
                while True:
                    status_response = requests.get(f"{API_BASE_URL}/normalize/status/{task_id}")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        
                        if status_data.get("status") == "PROCESSING":
                            time.sleep(1) # Спим 1 секунду и спрашиваем снова
                            continue
                            
                        elif status_data.get("status") == "COMPLETED":
                            # Задача выполнена, распаковываем результат
                            data = status_data["results"][0]
                            review_status = data.get("status")
                            golden_id = data.get("golden_id")
                            standard_name = data.get("standard_name")
                            confidence = data.get("confidence_score")

                            st.markdown("### Результат сопоставления:")

                            # Красиво бьем ответ на 3 плашки
                            col1, col2, col3 = st.columns([1, 2, 1])

                            with col1:
                                st.caption("Вердикт системы:")
                                if review_status == "AUTO_MAPPED":
                                    st.success("🟢 АВТО-СВЯЗКА (>=0.85)")
                                elif review_status == "REQUIRES_HUMAN_REVIEW":
                                    st.warning("🟡 НА РУЧНОЙ АППРУВ")
                                else:
                                    st.error("🔴 АНОМАЛИЯ / МУСОР")

                            with col2:
                                st.caption("Золотая запись в НСИ (Golden Record):")
                                if golden_id:
                                    st.markdown(
                                        f"**ID `{golden_id}`** : {standard_name}"
                                    )
                                else:
                                    st.write("— *Нет безопасного совпадения* —")

                            with col3:
                                st.caption("Confidence Score (L2-Cosine):")
                                if confidence is not None:
                                    st.metric("", f"{confidence:.2%}")
                                else:
                                    st.metric("", "0.0%")
                            
                            break # Выходим из цикла
                            
                        elif status_data.get("status") == "FAILED":
                            st.error(f"Сбой ML-воркера: {status_data.get('error')}")
                            break
                    else:
                        st.error(f"Ошибка проверки статуса. Код ответа: {status_response.status_code}")
                        break

        else:
            st.error(f"Ошибка постановки задачи. Код ответа: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error("Критическая ошибка: Невозможно связаться с FastAPI на порту 8000.")

st.markdown("---")
st.markdown(
    "💡 *Попробуйте ввести заведомо искаженные варианты: «ВВГнг ls 3 на 1.5» или «гофра пвх 20 с зондом»*"
)