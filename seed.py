import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from sqlalchemy import create_engine, text
import time

# --- НАСТРОЙКИ ---
FILE_PATH = "Выгрузка справочника РСБУ 03.07.2026.xlsx"
DATABASE_URL = "postgresql://mdm_user:mdm_password@postgres_db:5432/mdm_database"
LIMIT = 5000
BATCH_SIZE = 100

print("[1/4] Загрузка Excel файла в память...")
df = pd.read_excel(FILE_PATH, sheet_name='TDSheet')
df = df.dropna(subset=['НаименованиеПолное']).sample(n=LIMIT, random_state=42)
records = df['НаименованиеПолное'].tolist()

print("[2/4] Инициализация ML-модели RuBERT-tiny2...")
tokenizer = AutoTokenizer.from_pretrained("cointegrated/rubert-tiny2")
model = AutoModel.from_pretrained("cointegrated/rubert-tiny2")

def embed_texts(texts):
    encoded_input = tokenizer(texts, padding=True, truncation=True, return_tensors='pt', max_length=512)
    with torch.no_grad():
        model_output = model(**encoded_input)
    embeddings = model_output.last_hidden_state[:, 0, :]
    return embeddings.numpy().tolist()

print(f"[3/4] Векторизация {LIMIT} записей. Это займет пару минут...")
start_time = time.time()
vectors = []
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i+BATCH_SIZE]
    vectors.extend(embed_texts(batch))
print(f"Векторизация завершена за {round(time.time() - start_time, 1)} сек.")

print("[4/4] Сохранение в PostgreSQL...")
engine = create_engine(DATABASE_URL)
with engine.begin() as conn:
    # 1. Активируем расширение для векторного поиска
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    
    # 2. Жестко создаем таблицу, если ее не было (размерность 312 под RuBERT-tiny2)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS golden_records (
            id SERIAL PRIMARY KEY,
            standard_name TEXT NOT NULL,
            embedding vector(312)
        );
    """))
    
    # 3. Очищаем таблицу от старого мусора
    conn.execute(text("TRUNCATE TABLE golden_records RESTART IDENTITY CASCADE;"))
    
    # 4. Заливаем новые данные
    for i in range(len(records)):
        sql = text("""
            INSERT INTO golden_records (standard_name, embedding) 
            VALUES (:name, :emb)
        """)
        conn.execute(sql, {"name": records[i], "emb": str(vectors[i])})

print("✅ Операция успешна! Мастер-каталог на 5000 записей залит в базу.")