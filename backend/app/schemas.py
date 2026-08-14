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


class ReparseRequest(BaseModel):
    """错题 AI 重跑解析请求：仅传 keys 相关字段，content/subject/kp 从数据库读取。
    用法：前端 store 在用户配置好真实 API Key 后调用本端点，把"已测试通过 + 所有 keys"透传过来，
    让后端按 preferred → priority 轮询可用 provider 重跑一次 ai_analysis。
    """
    provider: str = ""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    try_fallback: bool = True
    preferred_providers: List[str] = []
    all_api_keys: Dict[str, str] = {}
    all_base_urls: Dict[str, str] = {}


class ClassifyRequest(BaseModel):
    """轻量学科分类请求：录入题目时实时调用，仅返回 subject + knowledge_points。
    字段含义与 MistakeCreate 一致（透传 provider/api_key/base_url/fallback/preferred 等）。
    """
    content: str
    provider: str = ""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    try_fallback: bool = True
    preferred_providers: List[str] = []
    all_api_keys: Dict[str, str] = {}
    all_base_urls: Dict[str, str] = {}


# ==================== 答题圈 Schemas ====================

class CommunityPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    summary: str = ""
    subject: str = ""
    author_name: str
    author_color: str = "#3B82F6"
    view_count: int = 0
    like_count: int = 0
    share_count: int = 0
    comment_count: int = 0
    created_at: datetime
    liked: bool = False           # 当前设备是否已点赞
    mine: bool = False            # 当前设备是否为作者（用于显示删除按钮）


class CommunityPostDetailOut(CommunityPostOut):
    full_text: str = ""
    solution: str = ""


class CommunityPostCreate(BaseModel):
    title: str
    summary: str = ""
    full_text: str = ""
    solution: str = ""
    subject: str = ""
    author_name: str


class CommunityCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_id: int
    author_name: str
    author_color: str = "#10B981"
    content: str
    like_count: int = 0
    created_at: datetime


class CommunityCommentCreate(BaseModel):
    author_name: str
    content: str
