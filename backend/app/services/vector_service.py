"""ChromaDB 向量检索：错题嵌入 + 相似题召回。

注意：首次使用默认 embedding 函数（all-MiniLM-L6-v2）会自动下载模型，需联网。
如需中文更优效果，可安装 sentence-transformers 并传 embedding_function。
"""
from typing import List, Optional

from app.config import get_settings

_client = None


def _db():
    global _client
    if _client is None:
        try:
            import chromadb

            _client = chromadb.PersistentClient(path=get_settings()["chroma_dir"])
        except Exception as e:
            _client = e  # 记录异常对象
    return _client


def _col():
    db = _db()
    if isinstance(db, Exception):
        return None
    try:
        return db.get_or_create_collection("mistakes", metadata={"hnsw:space": "cosine"})
    except Exception:
        return None


def upsert_mistake(mistake_id: int, content: str, metadata: Optional[dict] = None) -> bool:
    col = _col()
    if col is None:
        return False
    try:
        col.upsert(
            ids=[str(mistake_id)],
            documents=[content],
            metadatas=[metadata or {}],
        )
        return True
    except Exception:
        return False


def delete_mistake(mistake_id: int) -> None:
    col = _col()
    if col is None:
        return
    try:
        col.delete(ids=[str(mistake_id)])
    except Exception:
        pass


def search_similar(content: str, k: int = 3) -> List[dict]:
    """返回 [{id, subject, distance}]，未就绪/异常返回空列表。"""
    col = _col()
    if col is None:
        return []
    try:
        res = col.query(query_texts=[content], n_results=k)
        ids = res.get("ids", [[]])[0]
        dists = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        return [
            {
                "id": int(i),
                "subject": (m or {}).get("subject", ""),
                "distance": round(float(d), 4),
            }
            for i, d, m in zip(ids, dists, metas)
        ]
    except Exception:
        return []
