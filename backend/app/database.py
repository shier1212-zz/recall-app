"""SQLite（SQLAlchemy ORM）连接管理。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

engine = create_engine(
    get_settings()["database_url"],
    connect_args={"check_same_thread": False},  # SQLite + FastAPI 多线程
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
