"""答题圈：帖子 / 评论 / 点赞 / 分享。

设备号机制：无用户系统，前端生成 device_id 存 localStorage，请求 header 带 X-Device-Id；
用于点赞去重、删除/编辑权限校验。
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter()


# ---------- 工具：补齐 comment_count + liked + mine ----------

def _enrich_posts(
    posts: List[models.CommunityPost],
    device_id: str,
    db: Session,
) -> List[dict]:
    """把 SQLAlchemy 对象转成 dict，并补充 comment_count / liked / mine 三个运行时字段。"""
    if not posts:
        return []
    ids = [p.id for p in posts]
    # 评论数：一次性 group_by
    cnt_rows = db.query(
        models.CommunityComment.post_id,
        func.count(models.CommunityComment.id)
    ).filter(models.CommunityComment.post_id.in_(ids)).group_by(models.CommunityComment.post_id).all()
    cnt_map = {pid: c for pid, c in cnt_rows}
    # 我点过的
    my_likes = {
        l.post_id for l in db.query(models.CommunityLike)
        .filter(models.CommunityLike.post_id.in_(ids), models.CommunityLike.device_id == device_id).all()
    }
    out: List[dict] = []
    for p in posts:
        d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        d["comment_count"] = cnt_map.get(p.id, 0)
        d["liked"] = p.id in my_likes
        d["mine"] = bool(p.author_device and p.author_device == device_id)
        out.append(d)
    return out


# ---------- 帖子 ----------

@router.get("/community/posts", response_model=List[schemas.CommunityPostOut])
def list_posts(
    db: Session = Depends(get_db),
    x_device_id: str = Header(default="", alias="X-Device-Id"),
):
    rows = db.query(models.CommunityPost).order_by(desc(models.CommunityPost.id)).limit(200).all()
    return _enrich_posts(rows, device_id=x_device_id, db=db)


@router.post("/community/posts", response_model=schemas.CommunityPostDetailOut)
def create_post(
    payload: schemas.CommunityPostCreate,
    db: Session = Depends(get_db),
    x_device_id: str = Header(default="", alias="X-Device-Id"),
):
    if not payload.title.strip():
        raise HTTPException(400, "标题不能为空")
    # 自动从标题生成摘要（取前 80 字）
    summary = payload.summary.strip() or payload.title.strip()[:80]
    # 头像色：基于昵称 hash 出一个稳定颜色
    color = _color_from_name(payload.author_name)
    p = models.CommunityPost(
        title=payload.title.strip(),
        summary=summary,
        full_text=payload.full_text,
        solution=payload.solution,
        subject=payload.subject,
        author_name=payload.author_name.strip() or "匿名",
        author_color=color,
        author_device=x_device_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d["comment_count"] = 0
    d["liked"] = False
    d["mine"] = bool(x_device_id)
    return d


@router.get("/community/posts/{post_id}", response_model=schemas.CommunityPostDetailOut)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    x_device_id: str = Header(default="", alias="X-Device-Id"),
):
    p = db.get(models.CommunityPost, post_id)
    if not p:
        raise HTTPException(404, "帖子不存在")
    # 浏览 +1（极简；不去重，避免漏增计数）
    p.view_count = (p.view_count or 0) + 1
    db.commit()
    db.refresh(p)
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d["comment_count"] = db.query(func.count(models.CommunityComment.id)).filter(
        models.CommunityComment.post_id == post_id).scalar() or 0
    d["liked"] = db.query(models.CommunityLike).filter(
        models.CommunityLike.post_id == post_id,
        models.CommunityLike.device_id == x_device_id,
    ).first() is not None
    d["mine"] = bool(p.author_device and p.author_device == x_device_id)
    return d


@router.delete("/community/posts/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    x_device_id: str = Header(default="", alias="X-Device-Id"),
):
    p = db.get(models.CommunityPost, post_id)
    if not p:
        raise HTTPException(404, "帖子不存在")
    if not x_device_id or p.author_device != x_device_id:
        raise HTTPException(403, "只能删除自己发布的帖子")
    db.delete(p)
    db.commit()
    return {"ok": True, "deleted": post_id}


class ShareRequest(BaseModel):
    pass


@router.post("/community/posts/{post_id}/share")
def share_post(post_id: int, db: Session = Depends(get_db)):
    p = db.get(models.CommunityPost, post_id)
    if not p:
        raise HTTPException(404, "帖子不存在")
    p.share_count = (p.share_count or 0) + 1
    db.commit()
    db.refresh(p)
    return {"ok": True, "share_count": p.share_count}


@router.post("/community/posts/{post_id}/like")
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    x_device_id: str = Header(default="", alias="X-Device-Id"),
):
    """切换点赞：已点 → 取消；未点 → 加 1。"""
    if not x_device_id:
        raise HTTPException(400, "缺少设备号，无法点赞")
    p = db.get(models.CommunityPost, post_id)
    if not p:
        raise HTTPException(404, "帖子不存在")
    existing = db.query(models.CommunityLike).filter(
        models.CommunityLike.post_id == post_id,
        models.CommunityLike.device_id == x_device_id,
    ).first()
    if existing:
        db.delete(existing)
        p.like_count = max(0, (p.like_count or 0) - 1)
        liked = False
    else:
        db.add(models.CommunityLike(post_id=post_id, device_id=x_device_id))
        p.like_count = (p.like_count or 0) + 1
        liked = True
    db.commit()
    db.refresh(p)
    return {"ok": True, "liked": liked, "like_count": p.like_count}


# ---------- 评论 ----------

@router.get("/community/posts/{post_id}/comments", response_model=List[schemas.CommunityCommentOut])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    rows = db.query(models.CommunityComment).filter(
        models.CommunityComment.post_id == post_id
    ).order_by(models.CommunityComment.id.asc()).all()
    return rows


@router.post("/community/posts/{post_id}/comments", response_model=schemas.CommunityCommentOut)
def add_comment(
    post_id: int,
    payload: schemas.CommunityCommentCreate,
    db: Session = Depends(get_db),
):
    if not payload.content.strip():
        raise HTTPException(400, "评论内容不能为空")
    p = db.get(models.CommunityPost, post_id)
    if not p:
        raise HTTPException(404, "帖子不存在")
    color = _color_from_name(payload.author_name)
    c = models.CommunityComment(
        post_id=post_id,
        author_name=payload.author_name.strip() or "匿名",
        author_color=color,
        content=payload.content.strip(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------- 颜色生成（按昵称 hash，稳定） ----------

def _color_from_name(name: str) -> str:
    """从字符串生成稳定的色相。"""
    palette = [
        "#5E5CE6", "#FF9F0A", "#FF453A", "#30D158", "#34C759",
        "#AC8E68", "#FF375F", "#0A84FF", "#BF5AF2", "#64D2FF",
        "#A78BFA", "#F472B6", "#22D3EE", "#FB923C", "#4ADE80",
    ]
    h = 0
    for ch in name or "匿名":
        h = (h * 31 + ord(ch)) & 0xFFFF
    return palette[h % len(palette)]