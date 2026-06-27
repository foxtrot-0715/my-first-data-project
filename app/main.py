from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api.endpoints import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # Авто-создание таблиц СУБД при старте
    yield


app = FastAPI(
    title="MDM AI Lakehouse Core",
    description="Микросервис дедупликации и нормализации мастер-данных предприятия на базе RuBERT-tiny2",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1", tags=["Master Data"])


@app.get("/", include_in_schema=False)
def health_check():
    return {
        "status": "online",
        "service": "MDM Matcher v1.0",
        "swagger_docs": "/docs",
    }