"""Recall AI 错题本 - FastAPI 入口。

启动：cd backend && uvicorn app.main:app --reload --port 8000
文档：http://localhost:8000/docs
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import models, seed
from app.database import Base, engine
from app.routers import ai, chat, mistakes

Base.metadata.create_all(bind=engine)


def migrate_columns():
    """为已有库补充 SM-2 字段（不删数据）。列已存在则跳过。"""
    cols = [
        ("easiness_factor", "FLOAT"),
        ("interval_days", "INTEGER"),
        ("due_date", "DATETIME"),
    ]
    with engine.connect() as conn:
        for name, typ in cols:
            try:
                conn.execute(text(f"ALTER TABLE mistakes ADD COLUMN {name} {typ}"))
                conn.commit()
            except Exception:
                # sqlite: 列已存在会抛错，忽略即可
                conn.rollback()


migrate_columns()

# CORS：收紧为明确的前端来源（避免 `*` + credentials 的安全隐患）
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_allow_origins = [o.strip() for o in os.environ.get("BACKEND_CORS_ORIGINS", _default_origins).split(",") if o.strip()]
app = FastAPI(title="Recall AI 错题本 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mistakes.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.on_event("startup")
def on_startup():
    seed.ensure_seed()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "recall-api"}
