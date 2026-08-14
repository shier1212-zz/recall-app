"""AI 分析 / 变式题 / 批改 / OCR / 统计 / 相似题 / PDF & Markdown 导出。"""
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import ai_service, ocr_service, vector_service

router = APIRouter(tags=["ai"])

# ReportLab 中文 CID 字体（无需字体文件即可输出中文 PDF）
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


# ---------------- AI 能力 ----------------
@router.post("/ai/analyze")
def analyze(payload: schemas.AnalyzeRequest):
    """错题 AI 解析：学科 / 知识点 / 错因 / 解析。"""
    return ai_service.analyze_mistake(payload.content)


@router.post("/ai/classify-subject")
def classify_subject(payload: schemas.ClassifyRequest):
    """轻量学科分类：录入题目时实时调用，仅返回 subject + knowledge_points。
    复用 analyze_mistake 的 fallback 轮询逻辑（优先级：provider → preferred → priority）。
    全失败时返回 ai_status='fallback'，subject='未分类'，并通过 tried/reason 给出失败原因。"""
    preferred = payload.preferred_providers or []
    api_key_overrides: dict = dict(payload.all_api_keys or {})
    if payload.provider and payload.api_key:
        api_key_overrides[payload.provider] = payload.api_key
    base_url_overrides: dict = dict(payload.all_base_urls or {})
    if payload.provider and payload.base_url:
        base_url_overrides[payload.provider] = payload.base_url
    return ai_service.classify_subject(
        payload.content,
        provider=payload.provider,
        api_key=payload.api_key,
        api_key_overrides={**api_key_overrides, "__preferred__": (preferred[0] if preferred else None)},
        base_url=payload.base_url,
        base_url_overrides=base_url_overrides,
        try_fallback=payload.try_fallback,
        exclude_providers=[],
    )


@router.post("/ai/variant")
def variant(payload: schemas.AnalyzeRequest):
    """同知识点变式题生成。"""
    return {"variant": ai_service.generate_variant(payload.content)}


@router.post("/ai/grade")
def grade(payload: dict):
    """AI 自动批改。"""
    return {
        "grade": ai_service.grade_answer(
            payload.get("question", ""), payload.get("answer", "")
        )
    }


# ---------------- OCR ----------------
@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "空文件")
    try:
        text = ocr_service.recognize(data)
        return {"text": text, "subject": ""}
    except ocr_service.OcrUnavailable as e:
        # 503：依赖未安装，前端 catch 走 toast 提示用户安装
        raise HTTPException(
            status_code=503,
            detail={"code": "ocr_unavailable", "message": str(e)},
        )
    except ocr_service.OcrFailed as e:
        # 500：依赖装了但本次识别失败（图片格式 / 内部错误），让用户重传图
        raise HTTPException(
            status_code=500,
            detail={"code": "ocr_failed", "message": str(e)},
        )


# ---------------- 统计 / 相似题 ----------------
@router.get("/analysis/overview")
def overview(db: Session = Depends(get_db)):
    """学习看板真实聚合数据（替换原写死演示）。"""
    total = db.query(models.Mistake).count()
    reviewed = db.query(models.Mistake).filter(models.Mistake.reviewed.is_(True)).count()
    cats = db.query(models.Category).count()
    now = datetime.utcnow()
    due_today = (
        db.query(models.Mistake)
        .filter(models.Mistake.due_date.isnot(None), models.Mistake.due_date <= now)
        .count()
    )
    # 学科分布
    subj_rows = (
        db.query(models.Mistake.subject, func.count(models.Mistake.id))
        .group_by(models.Mistake.subject)
        .order_by(func.count(models.Mistake.id).desc())
        .all()
    )
    subject_stats = [{"subject": s or "未分类", "count": c} for s, c in subj_rows]
    # 近 7 天每日录入量（趋势）
    today = date.today()
    trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        cnt = db.query(models.Mistake).filter(func.date(models.Mistake.created_at) == d).count()
        trend.append({"date": d.isoformat(), "count": cnt})
    return {
        "total": total,
        "reviewed": reviewed,
        "todo": total - reviewed,
        "categories": cats,
        "due_today": due_today,
        "subject_stats": subject_stats,
        "trend": trend,
    }


@router.get("/analysis/similar")
def similar(content: str = "", k: int = 3):
    """基于向量库召回相似错题。"""
    return {"items": vector_service.search_similar(content, k)}


# ---------------- PDF 导出（ReportLab） ----------------
@router.get("/export/pdf")
def export_pdf(db: Session = Depends(get_db)):
    mistakes = db.query(models.Mistake).order_by(models.Mistake.created_at.desc()).all()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setTitle("Recall 错题报告")
    c.setFont("STSong-Light", 16)
    c.drawString(20 * mm, h - 20 * mm, f"Recall AI 错题本 · 学习报告 {datetime.now():%Y-%m-%d}")
    y = h - 32 * mm
    c.setFont("STSong-Light", 9)
    for i, m in enumerate(mistakes, 1):
        if y < 30 * mm:
            c.showPage()
            y = h - 20 * mm
            c.setFont("STSong-Light", 9)
        status = "已掌握" if m.reviewed else "未掌握"
        c.drawString(15 * mm, y, f"{i}. [{m.subject}] {status}（复习{m.review_count}次）来源：{m.source}")
        y -= 5 * mm
        content = m.content if len(m.content) <= 58 else m.content[:55] + "…"
        c.drawString(20 * mm, y, content)
        y -= 8 * mm
    c.save()
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=recall_report.pdf"},
    )


# ---------------- Markdown 导出（F8：补齐 PRD 要求的 Markdown 错题清单） ----------------
@router.get("/export/markdown")
def export_markdown(db: Session = Depends(get_db)):
    mistakes = db.query(models.Mistake).order_by(models.Mistake.created_at.desc()).all()
    lines: list[str] = [
        "# Recall AI 错题本 · 错题清单\n",
        f"> 导出时间：{datetime.now():%Y-%m-%d %H:%M} · 共 {len(mistakes)} 题\n",
    ]
    by_subject: dict[str, list] = {}
    for m in mistakes:
        by_subject.setdefault(m.subject or "未分类", []).append(m)
    for subj, items in by_subject.items():
        lines.append(f"\n## {subj}（{len(items)} 题）\n")
        for i, m in enumerate(items, 1):
            status = "✅ 已掌握" if m.reviewed else "⏳ 待复习"
            lines.append(f"### {i}. {status} · 复习 {m.review_count} 次\n")
            lines.append(f"**题目**：{m.content}\n")
            if m.knowledge_points:
                lines.append(f"**知识点**：{', '.join(m.knowledge_points)}\n")
            if m.ai_analysis:
                lines.append(f"**解析**：{m.ai_analysis}\n")
            lines.append("---\n")
    md = "".join(lines).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(md),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=recall_mistakes.md"},
    )
