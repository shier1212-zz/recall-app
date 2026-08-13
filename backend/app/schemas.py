"""Pydantic Schema（请求/响应模型）。"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    color: str
    count: int = 0


class CategoryCreate(BaseModel):
    name: str
    color: str = "#3B82F6"


class MistakeCreate(BaseModel):
    content: str
    subject: str = ""
    knowledge_points: List[str] = []
    source: str = ""
    category_id: int = 1
    # AI 解析用：前端用户填的 provider + api_key（来自 localStorage）。
    provider: str = ""
    api_key: Optional[str] = None
    # 当前 provider 的 base_url（用户在前端表单填写的，会覆盖后端默认 base）
    base_url: Optional[str] = None
    # 前端"自动调用连接成功的 AI"：失败时是否让后端自动换下一个 provider 重试
    try_fallback: bool = True
    # 前端记录的"已测试通过"的 provider 列表（按时间倒序），后端优先尝试这些
    preferred_providers: List[str] = []
    # 前端配置的所有 API Key（{deepseek: 'sk-...', siliconflow: 'sk-...', zhipu: 'sk-...'}）
    # 让后端 fallback 时能直接用上其他 provider 的 key，不用再问前端
    all_api_keys: Dict[str, str] = {}
    # 前端配置的所有 base_url（{deepseek: '...', zhipu: '...', siliconflow: '...'}）
    # 让后端 fallback 时按 provider 选用对应的 base_url
    all_base_urls: Dict[str, str] = {}


class MistakeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int
    content: str
    subject: str
    knowledge_points: List[str]
    source: str
    review_count: int
    reviewed: bool
    ai_analysis: str
    created_at: datetime
    # AI 解析状态：
    #   'ok'       → 真模型解析成功（拿到合法 JSON）
    #   'partial'  → 模型有响应但 JSON 不合法（保留原文作 ai_analysis）
    #   'fallback' → 降级（key 失效 / 网络错误 等完全没拿到响应）
    ai_status: str = "fallback"
    # 实际用了哪个 provider
    provider: str = ""
    # SM-2 记忆曲线字段（旧数据行可能为 NULL，故均允许 Optional）
    easiness_factor: Optional[float] = 2.5
    interval_days: Optional[int] = 0
    due_date: Optional[datetime] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    provider: str = "deepseek"   # mock | deepseek | zhipu | siliconflow
    api_key: Optional[str] = None  # 用户前端填写的密钥，仅本次请求使用，不落库
    base_url: Optional[str] = None  # 用户前端填写的 base_url（如自部署中转站）


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = []


class ReviewRequest(BaseModel):
    """一题一题复习动作：mastered=已掌握 / unmastered=还不太会 / skip=跳过"""
    result: str  # mastered | unmastered | skip


class AnalyzeRequest(BaseModel):
    content: str
