"""错题与分类 CRUD。"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import ai_service, vector_service

router = APIRouter(tags=["mistakes"])


# ---------------- 分类 ----------------
@router.get("/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(models.Category).order_by(models.Category.id).all()
    return [
        schemas.CategoryOut(id=c.id, name=c.name, color=c.color, count=len(c.mistakes))
        for c in cats
    ]


@router.post("/categories", response_model=schemas.CategoryOut)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="错题本名称不能为空")
    c = models.Category(name=name, color=payload.color or "#3B82F6")
    db.add(c)
    db.commit()
    db.refresh(c)
    return schemas.CategoryOut(id=c.id, name=c.name, color=c.color, count=0)


# ---------------- 错题 ----------------
@router.get("/mistakes", response_model=list[schemas.MistakeOut])
def list_mistakes(
    category_id: Optional[int] = None,
    q: str = "",
    reviewed: Optional[str] = None,  # true / false
    due: Optional[str] = None,        # "today" → 今日到期（SM-2）
    limit: int = 100000,              # 分页（默认全量，兼容旧前端）
    offset: int = 0,
    db: Session = Depends(get_db),
):
    qb = db.query(models.Mistake).order_by(models.Mistake.created_at.desc())
    if category_id:
        qb = qb.filter(models.Mistake.category_id == category_id)
    if reviewed == "true":
        qb = qb.filter(models.Mistake.reviewed.is_(True))
    elif reviewed == "false":
        qb = qb.filter(models.Mistake.reviewed.is_(False))
    if due == "today":
        now = datetime.utcnow()
        qb = qb.filter(models.Mistake.due_date.isnot(None), models.Mistake.due_date <= now)
    if q.strip():
        like = f"%{q.strip()}%"
        qb = qb.filter(
            models.Mistake.content.like(like) | models.Mistake.subject.like(like)
        )
    return qb.limit(limit).offset(offset).all()


@router.post("/mistakes", response_model=schemas.MistakeOut)
def create_mistake(
    payload: schemas.MistakeCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # ---------- 入参校验（F4：防止空题/孤儿题） ----------
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="题目内容不能为空")
    cat = db.get(models.Category, payload.category_id)
    if not cat:
        raise HTTPException(status_code=422, detail=f"错题本不存在：id={payload.category_id}")

    # 调 AI 解析：前端可显式传 provider+api_key（来自 localStorage），并附带"已测试通过的 provider"和"所有 key"
    # 后端会按：① 显式 provider ② preferred_providers[0] ③ priority 中的剩余 provider 顺序自动轮询
    # 这样用户只要有一个能用的 provider，错题解析就能成功
    preferred = payload.preferred_providers or []
    api_key_overrides: dict = dict(payload.all_api_keys or {})  # 所有前端 key 都带过去
    # 显式传的 api_key 优先级最高
    if payload.provider and payload.api_key:
        api_key_overrides[payload.provider] = payload.api_key
    # base_url 也同理：把前端填的所有 base_url 都带过去，fallback 时按 provider 选用
    base_url_overrides: dict = dict(payload.all_base_urls or {})
    if payload.provider and payload.base_url:
        base_url_overrides[payload.provider] = payload.base_url

    ai = ai_service.analyze_mistake(
        payload.content,
        provider=payload.provider,
        api_key=payload.api_key,
        api_key_overrides={**api_key_overrides, "__preferred__": (preferred[0] if preferred else None)},
        base_url=payload.base_url,
        base_url_overrides=base_url_overrides,
        try_fallback=payload.try_fallback,
        exclude_providers=[],
    )
    m = models.Mistake(
        category_id=payload.category_id,
        content=payload.content,
        subject=payload.subject or ai["subject"],
        knowledge_points=payload.knowledge_points or ai["knowledge_points"],
        source=payload.source,
        ai_analysis=ai["ai_analysis"],
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    # 写入向量库供相似题召回：异步 BackgroundTask（chroma 首次启动需下载模型，异步执行避免阻塞响应）
    background.add_task(_safe_vector_upsert, m.id, m.content, {"subject": m.subject})
    return schemas.MistakeOut(
        id=m.id,
        category_id=m.category_id,
        content=m.content,
        subject=m.subject,
        knowledge_points=m.knowledge_points,
        source=m.source,
        review_count=m.review_count,
        reviewed=m.reviewed,
        ai_analysis=m.ai_analysis,
        created_at=m.created_at,
        ai_status=ai.get("ai_status", "fallback"),
        provider=ai.get("provider", ""),
    )


def _safe_vector_upsert(mistake_id: int, content: str, meta: dict) -> None:
    try:
        vector_service.upsert_mistake(mistake_id, content, meta)
    except Exception as ve:
        print(f"[vector] upsert_mistake {mistake_id} 失败（不影响主流程）: {ve}")


@router.patch("/mistakes/{mid}/toggle-review", response_model=schemas.MistakeOut)
def toggle_review(mid: int, db: Session = Depends(get_db)):
    m = db.get(models.Mistake, mid)
    if not m:
        raise HTTPException(404, "错题不存在")
    m.reviewed = not m.reviewed
    if m.reviewed:
        m.review_count += 1
    db.commit()
    db.refresh(m)
    return m


@router.post("/mistakes/{mid}/review", response_model=schemas.MistakeOut)
def review_mistake(mid: int, payload: schemas.ReviewRequest, db: Session = Depends(get_db)):
    """
    一题一题复习，并按 SM-2 遗忘曲线更新排程：
    - mastered   → reviewed=True，repetitions+1，间隔按 SM-2 延长，EF+0.1
    - unmastered → reviewed=False，repetitions+1，间隔重置为 1 天，EF-0.2（易错度上升）
    - skip       → 不修改状态
    """
    m = db.get(models.Mistake, mid)
    if not m:
        raise HTTPException(404, "错题不存在")
    result = (payload.result or "").lower()
    if result not in ("mastered", "unmastered", "skip"):
        raise HTTPException(400, "result 必须为 mastered/unmastered/skip")

    if result in ("mastered", "unmastered"):
        m.review_count += 1  # 即 SM-2 的 repetitions
        reps = m.review_count
        if result == "mastered":
            m.reviewed = True
            if reps == 1:
                interval = 1
            elif reps == 2:
                interval = 6
            else:
                interval = round(m.interval_days * m.easiness_factor)
            m.easiness_factor = min(3.0, m.easiness_factor + 0.1)
            m.interval_days = max(interval, 1)
        else:  # unmastered
            m.reviewed = False
            m.easiness_factor = max(1.3, m.easiness_factor - 0.2)
            m.interval_days = 1
        m.due_date = datetime.utcnow() + timedelta(days=m.interval_days)
    # skip: no-op
    db.commit()
    db.refresh(m)
    return m


@router.get("/review/plan", response_model=dict)
def review_plan(db: Session = Depends(get_db)):
    """SM-2 复习计划：返回今日到期、全部待复习、已掌握数量。"""
    now = datetime.utcnow()
    total = db.query(models.Mistake).count()
    reviewed = db.query(models.Mistake).filter(models.Mistake.reviewed.is_(True)).count()
    due_today = (
        db.query(models.Mistake)
        .filter(models.Mistake.due_date.isnot(None), models.Mistake.due_date <= now)
        .count()
    )
    todo = total - reviewed
    return {
        "total": total,
        "reviewed": reviewed,
        "todo": todo,
        "due_today": due_today,
    }


@router.delete("/mistakes/{mid}")
def delete_mistake(mid: int, db: Session = Depends(get_db)):
    m = db.get(models.Mistake, mid)
    if not m:
        raise HTTPException(404, "错题不存在")
    db.delete(m)
    db.commit()
    vector_service.delete_mistake(mid)
    return {"ok": True}
