"""AI 答疑会话（历史对话 + 消息）。"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import SessionLocal, get_db
from app.services import ai_service

router = APIRouter(tags=["chat"])


@router.get("/conversations", response_model=list[schemas.ConversationDetail])
def list_conversations(db: Session = Depends(get_db)):
    """列出全部会话（包含历史消息），让前端一次拉取就能渲染对话历史。"""
    convs = (
        db.query(models.Conversation)
        .order_by(models.Conversation.id.desc())
        .all()
    )
    # 直接返 SQLAlchemy 对象，因 ConversationOut/Detail 都用了 from_attributes，能正确序列化为含 messages 的详情
    return convs


@router.post("/conversations", response_model=schemas.ConversationOut)
def create_conversation(
    payload: Optional[dict] = Body(default={}), db: Session = Depends(get_db)
):
    c = models.Conversation(title=(payload or {}).get("title") or "新对话")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/conversations/{cid}/messages", response_model=list[schemas.MessageOut])
def list_messages(cid: int, db: Session = Depends(get_db)):
    conv = db.get(models.Conversation, cid)
    if not conv:
        raise HTTPException(404, "会话不存在")
    return conv.messages


class _TestConnectionRequest(BaseModel):
    provider: str  # mock | deepseek | zhipu | siliconflow
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # 可选：用户在前端表单填写的 base_url


@router.post("/test-connection")
def test_connection(payload: _TestConnectionRequest):
    """校验某个 provider 的 API Key 是否可用。
    返回 {ok, reason, model, latency_ms}。可选 base_url 用于自部署中转等场景。"""
    return ai_service.test_connection(payload.provider, payload.api_key, payload.base_url)


@router.post("/chat", response_model=schemas.MessageOut)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    if payload.conversation_id:
        conv = db.get(models.Conversation, payload.conversation_id)
        if not conv:
            raise HTTPException(404, "会话不存在")
    else:
        conv = models.Conversation(title=payload.message[:20] or "新对话")
        db.add(conv)
        db.flush()

    db.add(models.ChatMessage(conversation_id=conv.id, role="user", content=payload.message))
    reply = ai_service.chat_reply(payload.message, payload.provider, payload.api_key, payload.base_url)
    msg = models.ChatMessage(conversation_id=conv.id, role="assistant", content=reply)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.post("/chat/stream")
def chat_stream(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    """流式答疑（F5：满足 PRD 首字 < 2s）。text/plain 分块输出，前端按 token 渲染。"""
    if payload.conversation_id:
        conv = db.get(models.Conversation, payload.conversation_id)
        if not conv:
            raise HTTPException(404, "会话不存在")
    else:
        conv = models.Conversation(title=payload.message[:20] or "新对话")
        db.add(conv)
        db.flush()
    cid = conv.id
    db.add(models.ChatMessage(conversation_id=cid, role="user", content=payload.message))
    db.commit()

    def event_gen():
        pieces: list[str] = []
        try:
            for piece in ai_service.chat_reply_stream(payload.message, payload.provider, payload.api_key, payload.base_url):
                pieces.append(piece)
                yield piece
        finally:
            # 流式结束后落库 assistant 消息（独立会话，避免请求 db 已关闭）
            local_db = SessionLocal()
            try:
                local_db.add(models.ChatMessage(
                    conversation_id=cid, role="assistant", content="".join(pieces)
                ))
                local_db.commit()
            except Exception as ve:
                local_db.rollback()
                print(f"[chat/stream] 保存 assistant 消息失败: {ve}")
            finally:
                local_db.close()

    return StreamingResponse(event_gen(), media_type="text/plain; charset=utf-8")
