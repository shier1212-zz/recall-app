"""大模型服务：多 provider 支持（mock / deepseek / zhipu / siliconflow）。

所有 provider 走 OpenAI 兼容协议。密钥优先级：请求携带的 api_key > 后端环境变量；
都没有时自动降级为规则回复，保证接口可用。
"""
import json
import re
from typing import Optional, Tuple, Dict, Any

from app.config import get_settings

_clients: dict = {}  # cache key -> (client, model)


def _llm(provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> Optional[Tuple[object, str]]:
    """懒加载 OpenAI 兼容客户端。返回 (client, model) 或 None。

    优先级：
      base_url:   请求携带的 > 环境变量配置
      api_key:    请求携带的 > 环境变量配置
    cache key 同时包含 provider / key 尾号 / base_url 尾段，避免同 key 不同 base 误用旧 client。
    """
    s = get_settings()
    cfg = {
        "deepseek":    (s["deepseek_api_key"],    s["deepseek_base_url"],    s["deepseek_model"]),
        "zhipu":       (s["zhipu_api_key"],       s["zhipu_base_url"],       s["zhipu_model"]),
        "siliconflow": (s["siliconflow_api_key"], s["siliconflow_base_url"], s["siliconflow_model"]),
    }.get(provider)
    if not cfg:
        return None
    key, default_base, model = cfg
    if api_key and str(api_key).strip():
        key = str(api_key).strip()
    if base_url and str(base_url).strip():
        default_base = str(base_url).strip()
    if not key:
        return None
    # cache key 包含 key 尾号 + base_url 尾段，不同 base_url 视为不同 client
    base_tag = (default_base or "")[-24:]
    cache_key = f"{provider}:k{key[-8:]}:b{base_tag}"
    if cache_key not in _clients:
        from openai import OpenAI
        _clients[cache_key] = (OpenAI(api_key=key, base_url=default_base), model)
    return _clients[cache_key]


def _chat(
    provider: str, system: str, user: str,
    temperature: float = 0.3, max_tokens: int = 800,
    api_key: Optional[str] = None, base_url: Optional[str] = None,
) -> str:
    cli = _llm(provider, api_key, base_url)
    if cli is None:
        raise RuntimeError(f"{provider.upper()} API Key 未配置")
    client, model = cli
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


# ---------- 错误分类与人类可读化 ----------
# 用于把 openai SDK 异常翻成对用户友好的中文短句，便于前端气泡/Toast 直接展示
_PROVIDER_LABEL = {
    "deepseek":    "DeepSeek",
    "zhipu":       "智谱 GLM-4",
    "siliconflow": "硅基流动",
    "mock":        "本地规则",
}


def humanize_error(provider: str, exc: Exception) -> str:
    """把 openai/HTTP 异常翻译成中文短句（不含 provider 标签，由调用方拼）。"""
    s = str(exc)
    low = s.lower()
    if "authentication" in low or "401" in s or "invalid api key" in low or "incorrect api key" in low:
        return "Key 无效或已过期（请到该平台重新生成）"
    if "insufficient" in low or "quota" in low or "balance" in low or "402" in s:
        return "账户余额不足（请充值或换 Key）"
    if ("rate" in low and "limit" in low) or "429" in s:
        return "请求频率过高（稍后重试）"
    if "timed out" in low or "timeout" in low:
        return "请求超时（网络较慢）"
    if ("connection" in low or "resolve" in low or "network" in low) and "error" in low:
        return "网络异常（连接失败）"
    if "model" in low and ("not exist" in low or "not found" in low or "invalid" in low):
        return "模型名称不存在或无权访问"
    if "未配置" in s:
        return "暂未配置 API Key"
    return f"调用失败：{s[:140]}"


def _fallback(message: str, provider: str, error_reason: Optional[str] = None) -> str:
    """API Key 缺失或调用异常时的降级规则回复。
    error_reason 为 None 时表示"未配置 Key"；非 None 时表示"调用失败"，会把原因写进文案。"""
    if re.search("导数|切线|积分|函数|单调", message):
        body = "函数类问题：先求导 f'(x)，代入给定点得斜率，再结合 f(x0) 求切线；单调性看导数符号。"
    elif re.search("力|牛顿|物理|加速度|位移", message):
        body = "物理题先找合力：a=F/m，再由 v=v0+at、x=v0t+½at² 求解。"
    elif re.search("语法|虚拟|时态|insist", message):
        body = "语法点：insist/suggest 表\"坚持要求/建议\"时，从句用 (should)+动词原形。"
    else:
        body = "已收到你的问题。可在 AI 答疑页点击「🔑 设置 Key」填入对应平台密钥后获得大模型回答。"
    tag = _PROVIDER_LABEL.get(provider, "AI")
    if provider == "mock":
        return f"【{tag}】{body}"
    if error_reason is None:
        return f"（{tag} 暂未配置 API Key，已降级为规则回复）{body}"
    return f"（{tag} {error_reason}，已降级为规则回复）{body}"


# ---------- Provider 自动选择 ----------
# 默认优先级：deepseek → zhipu → siliconflow；都没有则降级 mock（规则回复）
_PROVIDER_PRIORITY = ("deepseek", "zhipu", "siliconflow")
_PROVIDER_KEY_FIELD = {
    "deepseek": "deepseek_api_key",
    "zhipu": "zhipu_api_key",
    "siliconflow": "siliconflow_api_key",
}


def _provider_has_key(provider: str, api_key_overrides: Optional[dict] = None) -> bool:
    """判断 provider 是否有可用 key：请求级 > 环境变量。"""
    s = get_settings()
    overrides = api_key_overrides or {}
    key = (overrides.get(provider) or s.get(_PROVIDER_KEY_FIELD.get(provider, ""), "") or "").strip()
    return bool(key)


def auto_pick_provider(api_key_overrides: Optional[dict] = None) -> str:
    """按优先级返回第一个有 key 的 provider；都没有返回 'mock'。"""
    for p in _PROVIDER_PRIORITY:
        if _provider_has_key(p, api_key_overrides):
            return p
    return "mock"


# ---------- 测试连接（API Key 校验） ----------
def test_connection(provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """验证 provider 是否能连通。
    返回 {ok: bool, reason: str, model: str, latency_ms: int}。
    可选 base_url：覆盖默认 base（前端用户在 API Key 设置里填的）。"""
    import time
    t0 = time.time()
    if provider == "mock":
        return {"ok": True, "reason": "本地规则模式，无需 Key", "model": "rule-based", "latency_ms": 0}
    cli = _llm(provider, api_key, base_url)
    if cli is None:
        return {"ok": False, "reason": "未配置 API Key", "model": "", "latency_ms": 0}
    client, model = cli
    try:
        # 用最小 token 调用一下，真实验证 Key + 网络 + 模型可访问
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            temperature=0,
            max_tokens=8,
            timeout=15,
        )
        latency = int((time.time() - t0) * 1000)
        _ = resp.choices[0].message.content
        return {"ok": True, "reason": "连通成功", "model": model, "latency_ms": latency}
    except Exception as e:
        latency = int((time.time() - t0) * 1000)
        return {"ok": False, "reason": humanize_error(provider, e), "model": model, "latency_ms": latency}


# ---------- 错题相关能力 ----------
def _log(tag: str, msg: str) -> None:
    """统一日志：打 stderr，方便 sandbox 日志/前端排查时查看。"""
    import sys
    print(f"[ai_service] {tag}: {msg}", file=sys.stderr, flush=True)


def _clean_ai_text(text: str, max_len: int = 800) -> str:
    """清洗模型原始输出里的噪声字符，使入库文本可读。

    处理对象：
      - ASCII 控制字符（除 \\n \\r \\t 外全去掉）
      - 替换字符 U+FFFD（U+FFFD 在乱码文本里常以连片出现）
      - 模型丢失中文标点时的替代符：◆ ◇ ■ ● ▲ ▼（连续出现视为噪声）
      - 被 token 化的拉丁文/西文（如 pérdida / é / í 等孤立出现在中文段落里）→
        任何含变音符号（U+00C0–U+024F）的拉丁词视为乱码插入，整词丢弃；
        纯 ASCII 英文术语（GPS/AI/Python 等）保留。
      - 连续空行/连续空白压缩为单个换行或单空格
      - 长度截断到 max_len（防御超长输出）

    这是"最后一道防线"——主防线仍然是 prompt + JSON 解析。
    """
    if not text:
        return ""
    s = text
    # 1) 替换字符 U+FFFD
    s = s.replace("\ufffd", "")
    # 2) ASCII 控制字符（保留 \n \r \t）
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)
    # 3) 模型替代符序列：连续 2 个以上 ◆/■/●/▲/▼/◇ 视为噪声行，整段去掉
    s = re.sub(r"[◆■▲▼●◇]{2,}", " ", s)
    # 4) 单个 ◆ 等作为中文标点替代时，直接去掉（比保留噪声更友好）
    for sym in ("◆", "■", "▲", "▼", "●", "◇"):
        s = s.replace(sym, "")
    # 5) 拉丁扩展字符噪声：含变音符号（é/á/ñ/ü…）的拉丁词视为乱码插入，整词丢弃。
    #    纯 ASCII 英文术语（GPS/AI/Python 等）不受影响。
    s = re.sub(r"[A-Za-z\u00C0-\u024F]*[\u00C0-\u024F][A-Za-z\u00C0-\u024F]*", " ", s)
    # 6) 连续空白行 / 多个空格 → 单换行 / 单空格
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.strip()
    # 7) 长度截断
    if len(s) > max_len:
        s = s[:max_len].rstrip() + "…"
    return s


def _parse_kp_fallback(raw_kp_field: str) -> list:
    """从 raw 里抠出来的 knowledge_points 字段值不一定是合法 JSON 数组。
    兼容：[...] / "a,b,c" / 'a','b' / a / b 等形式。
    抠不出合法项时返回空列表。"""
    if not raw_kp_field:
        return []
    s = raw_kp_field.strip()
    # 1) 尝试 JSON
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()][:5]
    except Exception:
        pass
    # 2) 剥括号 → 按 , 或 、 分隔
    s = s.strip("[]")
    parts = re.split(r"[,，、;；\n]+", s)
    out = []
    for p in parts:
        p = p.strip().strip("'\"`").strip()
        if p and p not in out:
            out.append(p)
        if len(out) >= 5:
            break
    return out


def _extract_ai_field_from_text(raw: str, field: str) -> str:
    """从可能非法的 JSON 字符串里用宽松正则抠出指定字段的字符串值。

    例：raw = '{ "subject":"地理", "ai_analysis": "对①◆...◇，地球..." }'
        field = "ai_analysis" → '对，地球...'
    支持：
      - 字段名带双引号 / 单引号 / 无引号
      - 值里允许未转义的真换行（multi-line），以启发式"遇到下一字段或 '} 作收尾
      - 值末尾常见污染（", " \", '\n 等）会顺手清掉
    抠不出来返回空串。
    """
    if not raw or not field:
        return ""
    # 尝试 1：找 "field"\s*:\s*"（支持到下一个 "field" 或 顶层的 "} 结束）
    # 用 lazy + 手动收尾
    pattern = re.compile(
        r'"' + re.escape(field) + r'"\s*:\s*"',  # "field":"
        re.IGNORECASE,
    )
    m = pattern.search(raw)
    if not m:
        return ""
    start = m.end()
    # 从 start 起找匹配的结束：状态机跟踪 \ 转义
    i = start
    buf: list[str] = []
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            # 处理 \" \\ \n \t 等转义
            nxt = raw[i + 1]
            if nxt == "n":
                buf.append("\n")
            elif nxt == "t":
                buf.append("\t")
            elif nxt == "r":
                buf.append("\r")
            elif nxt == '"':
                buf.append('"')
            elif nxt == "\\":
                buf.append("\\")
            else:
                buf.append(nxt)
            i += 2
            continue
        if ch == '"':
            # 字段结束
            break
        buf.append(ch)
        i += 1
    val = "".join(buf)
    # 后处理：去掉首尾的空白污染字符
    val = re.sub(r"[\ufffd\u200b-\u200f\ufeff]", "", val)
    return val.strip()


def _safe_json_loads(raw: str) -> Optional[dict]:
    """宽松 JSON 解析：兼容模型返回里夹杂的控制字符/单行注释/未转义换行等。
    依次尝试：① 清洗控制字符后标准解析 ② 抽取首段 {...} 块后解析 ③ 直接解析。
    """
    if not raw:
        return None
    s = raw.strip()
    # 去掉 <think>...</think> 之类推理块（部分模型会先写思考再出 JSON）
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    # 兼容 markdown ```json ... ``` 围栏
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.S)
    if fence:
        s = fence.group(1)
    # 清洗 ASCII 控制字符（保留 \n \r \t），其它一律去掉（防 JSON parse 时 Invalid control character）
    s_clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s)
    for candidate in (s_clean, s):
        try:
            v = json.loads(candidate)
            if isinstance(v, dict):
                return v
        except Exception:
            pass
    # 最后兜底：取首个 {...} 块（贪婪），容许 JSON 里有真换行
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        try:
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", m.group(0))
            v = json.loads(cleaned, strict=False)  # strict=False 容许裸 \n
            if isinstance(v, dict):
                return v
        except Exception:
            pass
    return None


def classify_subject(
    content: str,
    provider: str = "",
    api_key: Optional[str] = None,
    api_key_overrides: Optional[dict] = None,
    base_url: Optional[str] = None,
    base_url_overrides: Optional[dict] = None,
    try_fallback: bool = True,
    exclude_providers: Optional[list] = None,
) -> Dict[str, Any]:
    """轻量学科分类：仅返回 {subject, knowledge_points}，prompt 短、token 省，适合录入时实时调用。

    - 复用 auto_pick_provider + priority fallback 轮询逻辑（与 analyze_mistake 一致）
    - 不生成 error_reason / ai_analysis（与前端 UI 实时反馈的诉求对齐）
    - 全失败时返回 ai_status='fallback'，subject='未分类'，并把每个 provider 的失败原因带回 tried
    """
    exclude = set(exclude_providers or [])
    tried: list[dict] = []
    preferred = (api_key_overrides or {}).pop("__preferred__", None) if isinstance(api_key_overrides, dict) else None
    url_overrides: dict = dict(base_url_overrides or {})
    if provider and base_url and str(base_url).strip():
        url_overrides[provider] = str(base_url).strip()

    _SYSTEM_PROMPT = (
        "你是学科分类器。判断题目所属学科，候选：数学/物理/化学/生物/英语/语文/历史/政治/地理/信息/通用。"
        "严格输出一个 JSON 对象：{\"subject\": \"学科名\", \"knowledge_points\": [\"知识点1\", \"知识点2\"]}。"
        "只输出 JSON，无解释、无 markdown 围栏、无前缀。"
    )

    def _try_one(p: str, k: Optional[str], b: Optional[str]) -> Optional[dict]:
        if not p or p == "mock":
            return None
        cli = _llm(p, k, b)
        if cli is None:
            tried.append({"provider": p, "status": "no_key", "reason": "未配置 Key", "snippet": ""})
            _log(p, "未配置 Key，跳过")
            return None
        try:
            raw = _chat(
                p,
                _SYSTEM_PROMPT,
                content,
                temperature=0.1,
                max_tokens=120,
                api_key=k,
                base_url=b,
            )
        except Exception as e:
            reason = humanize_error(p, e)
            tried.append({"provider": p, "status": "api_error", "reason": reason, "snippet": str(e)[:80]})
            _log(p, f"调用失败: {reason}")
            return None

        data = _safe_json_loads(raw)
        if data and (data.get("subject") or data.get("knowledge_points")):
            tried.append({"provider": p, "status": "ok", "reason": "", "snippet": ""})
            return {
                "subject": str(data.get("subject", "")).strip() or "未分类",
                "knowledge_points": [str(x).strip() for x in (data.get("knowledge_points") or []) if str(x).strip()][:5],
            }

        # JSON 解析失败：用 _extract_subject_kp_from_text 在原始 raw 里兜底捞一次
        snippet = (raw or "").strip()[:200]
        subj, kp = _extract_subject_kp_from_text(raw or "")
        if subj or kp:
            tried.append({"provider": p, "status": "partial", "reason": "JSON 解析失败，已从原文兜底", "snippet": snippet[:80]})
            return {"subject": subj or "未分类", "knowledge_points": kp}

        tried.append({"provider": p, "status": "no_signal", "reason": "模型无有效输出", "snippet": snippet[:80]})
        return None

    # 1) 显式 provider
    if provider and provider not in exclude:
        r = _try_one(provider, api_key, base_url)
        if r:
            return {**r, "provider": provider, "ai_status": "ok"}
        exclude.add(provider)
    # 2) preferred（已测试通过的 provider，按时间倒序）
    if try_fallback and preferred and preferred not in exclude:
        ok = (api_key_overrides or {}).get(preferred) if isinstance(api_key_overrides, dict) else None
        ob = url_overrides.get(preferred)
        r = _try_one(preferred, ok, ob)
        if r:
            return {**r, "provider": preferred, "ai_status": "ok"}
        exclude.add(preferred)
    # 3) priority 轮询剩余可用 provider
    if try_fallback:
        for p in _PROVIDER_PRIORITY:
            if p in exclude:
                continue
            ok = (api_key_overrides or {}).get(p) if isinstance(api_key_overrides, dict) else None
            ob = url_overrides.get(p)
            if not ok and not _provider_has_key(p, api_key_overrides):
                continue
            r = _try_one(p, ok, ob)
            if r:
                return {**r, "provider": p, "ai_status": "ok"}
            exclude.add(p)

    # 全失败：降级 + 失败原因
    last_p = provider or (preferred if preferred in _PROVIDER_PRIORITY else auto_pick_provider(api_key_overrides)) or "mock"
    detail_lines = [f"· {_PROVIDER_LABEL.get(t['provider'], t['provider'])}: {t['status']} — {t['reason']}" for t in tried[:5]]
    return {
        "subject": "未分类",
        "knowledge_points": [],
        "provider": last_p,
        "ai_status": "fallback",
        "tried": tried,
        "reason": "\n".join(detail_lines) if detail_lines else "暂未配置 AI Key（到 AI 答疑页设置 Key 后可自动识别学科）",
    }


def _extract_subject_kp_from_text(text: str) -> tuple[str, list[str]]:
    """从纯文本里弱匹配出学科和知识点（兜底用，给无法解析 JSON 的小模型）。"""
    subjects = ["数学", "物理", "英语", "化学", "生物", "历史", "政治", "地理", "语文"]
    subj = ""
    for s in subjects:
        if s in text:
            subj = s
            break
    # 优先匹配「本题考查/关于/涉及」前后短语；否则按常见学科关键词兜底取
    kp: list[str] = []
    m = re.search(r"(?:考查|关于|涉及|属于|是)\s*([^，。；\n]{2,12})", text)
    if m:
        kp.append(m.group(1).strip())
    # 学科小标签兜底（导数/牛顿/虚拟语气/遗传/……）—— 出现在题干里直接收
    subject_hints = {
        "数学": ["导数", "切线", "积分", "函数", "单调", "极值", "不等式", "数列"],
        "物理": ["牛顿", "加速度", "位移", "力", "电场", "磁场", "光"],
        "英语": ["语法", "虚拟", "时态", "从句", "单词"],
        "化学": ["反应", "化学键", "元素", "摩尔"],
        "生物": ["细胞", "遗传", "DNA", "基因"],
        "历史": ["朝代", "战争", "革命"],
        "政治": ["哲学", "经济", "政治"],
        "地理": ["气候", "经度", "纬度", "公转", "自转"],
        "语文": ["古诗", "文言文", "作文"],
    }
    for kw in subject_hints.get(subj, []):
        if kw in text:
            kp.append(kw)
            break
    return subj, list(dict.fromkeys(kp))[:3]  # 去重，保留前 3 个


def analyze_mistake(
    content: str,
    provider: str = "",
    api_key: Optional[str] = None,
    api_key_overrides: Optional[dict] = None,
    base_url: Optional[str] = None,
    base_url_overrides: Optional[dict] = None,
    try_fallback: bool = False,  # 前端"自动调用连接成功的 AI"：失败时是否自动换下一个 provider
    exclude_providers: Optional[list] = None,  # 已试过且失败的 provider，跳过
) -> dict:
    """错题 AI 解析 → {subject, knowledge_points, error_reason, ai_analysis, provider, ai_status}

    ai_status: 'ok' 表示真正解析成功（JSON）；'partial' 表示模型有响应但 JSON 不合法（保留原文作 ai_analysis）；
                'fallback' 表示降级（key 失效 / 网络错误 等完全没拿到响应）
    当 try_fallback=True 且 provider 失败时，会自动按 priority 轮询下一个有 key 的 provider（不在 exclude 中）。

    base_url / base_url_overrides:
      base_url 是当前 provider 的 base_url（请求级覆盖默认 base）；
      base_url_overrides 是所有 provider 的 base_url（{deepseek:..., zhipu:..., siliconflow:...}），
      fallback 轮询时按 provider 查这里。
    """
    exclude = set(exclude_providers or [])
    # 选 provider 顺序：① 显式指定 ② 已测试通过的 provider（在 api_key_overrides['__preferred__'] 里） ③ auto pick
    tried: list[dict] = []  # [{provider, status, reason, snippet}] 记录每个 provider 的真实结局
    preferred = (api_key_overrides or {}).pop("__preferred__", None) if isinstance(api_key_overrides, dict) else None
    # base_url 表：fallback 轮询时按 provider 查
    url_overrides: dict = dict(base_url_overrides or {})
    if provider and base_url and str(base_url).strip():
        url_overrides[provider] = str(base_url).strip()

    def _try_one(p: str, k: Optional[str], b: Optional[str] = None) -> Optional[dict]:
        """返回 dict 表示真正解析成功；返回 None 表示失败/降级。
        失败时会在 tried 里追加 {provider, status, reason}。
        """
        if not p or p == "mock":
            return None
        cli = _llm(p, k, b)
        if cli is None:
            tried.append({"provider": p, "status": "no_key", "reason": "未配置 Key", "snippet": ""})
            _log(p, "未配置 Key，跳过")
            return None
        try:
            raw = _chat(
                p,
                "你是资深中学教师。请把学生的错题解析为严格 JSON，字段："
                "subject(学科，单一字符串)、knowledge_points(知识点，字符串数组，<=5 个)、"
                "error_reason(错因，1-2 句)、ai_analysis(完整分步解析)。"
                "只输出一个 JSON 对象，不要任何解释、思考、markdown 围栏或前缀。"
                "【重要】严格使用 ASCII 数字(1 2 3)与中文全角标点(，。：；！？),"
                "不要用 ◆■▲▼●◇ 等替代符,不要输出乱码/控制字符/西文片段。",
                content,
                api_key=k,
                base_url=b,
            )
        except Exception as e:
            reason = humanize_error(p, e)
            tried.append({"provider": p, "status": "api_error", "reason": reason, "snippet": str(e)[:120]})
            _log(p, f"调用失败: {reason} ({e})")
            return None

        data = _safe_json_loads(raw)
        if data:
            tried.append({"provider": p, "status": "ok", "reason": "", "snippet": str(data.get("ai_analysis", ""))[:80]})
            return {
                "provider": p,
                "subject": str(data.get("subject", "数学")),
                "knowledge_points": [str(x) for x in data.get("knowledge_points", [])][:5],
                "error_reason": str(data.get("error_reason", "")),
                "ai_analysis": str(data.get("ai_analysis", "")),
                "ai_status": "ok",
            }

        # JSON 解析失败：模型可能有响应，但格式不合法（小模型常见）。
        # 此时不再丢弃——优先从 raw 里抠出 ai_analysis/error_reason 字段值做兜底，
        # 抠不到再清洗原文后保留（仍标 'partial'），让用户至少能看到干净的内容。
        snippet = (raw or "").strip()[:400]
        tried.append({"provider": p, "status": "partial", "reason": "JSON 解析失败，已尝试字段抽取+清洗", "snippet": snippet})
        _log(p, f"JSON 解析失败，尝试字段抽取（前 80 字）: {snippet[:80]!r}")

        raw_ai = _extract_ai_field_from_text(raw or "", "ai_analysis")
        raw_err = _extract_ai_field_from_text(raw or "", "error_reason")
        raw_subj_field = _extract_ai_field_from_text(raw or "", "subject")
        raw_kp_field = _extract_ai_field_from_text(raw or "", "knowledge_points")

        # 字段抽取成功 → 直接当 ai_analysis，标 partial 但内容干净
        if raw_ai:
            cleaned_ai = _clean_ai_text(raw_ai, max_len=2000)
            if cleaned_ai:
                subj = raw_subj_field or ""
                return {
                    "provider": p,
                    "subject": subj or "数学",
                    "knowledge_points": _parse_kp_fallback(raw_kp_field) if raw_kp_field else [],
                    "error_reason": _clean_ai_text(raw_err, max_len=200),
                    "ai_analysis": cleaned_ai,
                    "ai_status": "partial",
                }

        # 字段抽取失败 → 清洗原文（去 ◆/控制字符/拉丁噪声）后保留
        if snippet:
            cleaned = _clean_ai_text(snippet, max_len=800)
            subj, kp = _extract_subject_kp_from_text(raw or "")
            if cleaned:
                return {
                    "provider": p,
                    "subject": (raw_subj_field or subj or "数学"),
                    "knowledge_points": _parse_kp_fallback(raw_kp_field) if raw_kp_field else kp,
                    "error_reason": _clean_ai_text(raw_err, max_len=200),
                    "ai_analysis": cleaned + "\n\n（提示：模型未按 JSON 输出，已清洗保留原文；如需更结构化结果，可在 AI 答疑页改用支持 JSON 的模型）",
                    "ai_status": "partial",
                }
        return None

    # 1. 按指定顺序尝试
    if provider and provider not in exclude:
        result = _try_one(provider, api_key, base_url)
        if result:
            return result
        exclude.add(provider)

    # 2. 已测试通过的 preferred（来自前端 store.providerHealth.passed）
    if try_fallback and preferred and preferred not in exclude:
        override_key = (api_key_overrides or {}).get(preferred) if isinstance(api_key_overrides, dict) else None
        override_base = url_overrides.get(preferred)
        result = _try_one(preferred, override_key, override_base)
        if result:
            return result
        exclude.add(preferred)

    # 3. 按 priority 轮询剩余有 key 的 provider
    if try_fallback:
        for p in _PROVIDER_PRIORITY:
            if p in exclude:
                continue
            override_key = (api_key_overrides or {}).get(p) if isinstance(api_key_overrides, dict) else None
            override_base = url_overrides.get(p)
            # 也要查 settings 里有没有 key（避免前端没传就跳过）
            if not override_key and not _provider_has_key(p, api_key_overrides):
                continue
            result = _try_one(p, override_key, override_base)
            if result:
                return result
            exclude.add(p)

    # 4. 都失败 → 返回最后一次降级，错误消息里透出每个 provider 的真实原因
    last_p = provider or (preferred if preferred in _PROVIDER_PRIORITY else auto_pick_provider(api_key_overrides))
    if not last_p or last_p not in _PROVIDER_PRIORITY:
        last_p = auto_pick_provider(api_key_overrides)

    # 把每个 provider 的失败原因压成 1-2 行短摘要
    detail_lines = []
    for t in tried[:5]:
        prov = t["provider"]
        label = _PROVIDER_LABEL.get(prov, prov)
        detail_lines.append(f"· {label}: {t['status']} — {t['reason']}")
    detail = "\n".join(detail_lines) if detail_lines else ""

    # mock 分支：用户根本没配置任何 Key，文案应是"未配置 Key"友好提示，不要写"调用失败"
    if last_p == "mock" or not last_p:
        ai_analysis = (
            "【本地规则】暂未配置 AI Key，已生成规则回复。\n\n"
            "到 AI 答疑页点击「🔑 设置 Key」填入 DeepSeek / 智谱 / 硅基流动 任一平台的密钥，"
            "再点「🧪 测试连接」验证可用后，即可获得大模型解析。"
        )
    else:
        base_msg = (
            f"（{_PROVIDER_LABEL.get(last_p, last_p or 'AI')} 调用失败：所有可用的 provider 均无法解析，"
            f"已生成降级解析）"
        )
        if detail:
            ai_analysis = f"{base_msg}\n\n各 provider 实际原因：\n{detail}\n\n请到 AI 答疑页点击「🔑 设置 Key」→「🧪 测试连接」验证可用性。"
        else:
            ai_analysis = f"{base_msg}\n\n请检查 API Key 或到 AI 答疑页点击「🔑 设置 Key」→ 🧪 测试连接 验证可用性。"

    return {
        "provider": last_p or "mock",
        "subject": "数学",
        "knowledge_points": ["待补充"],
        "error_reason": "",
        "ai_analysis": ai_analysis,
        "ai_status": "fallback",
        "tried": tried,
    }


def generate_variant(mistake_content: str, provider: str = "", api_key: Optional[str] = None, api_key_overrides: Optional[dict] = None, base_url: Optional[str] = None, base_url_overrides: Optional[dict] = None) -> str:
    if not provider or provider == "auto":
        provider = auto_pick_provider(api_key_overrides)
    if provider == "mock":
        return "（本地规则模式无法生成变式题，请配置 AI Key 后重试）"
    try:
        b = (base_url_overrides or {}).get(provider) if isinstance(base_url_overrides, dict) else None
        return _chat(
            provider,
            "你是命题教师。根据原题同知识点出一道变式题，输出【题目】【答案】【解析】。",
            mistake_content,
            temperature=0.8,
            api_key=api_key,
            base_url=b or base_url,
        )
    except Exception as e:
        return f"（{humanize_error(provider, e)}）变式题生成暂不可用。"


def grade_answer(question: str, answer: str, provider: str = "", api_key: Optional[str] = None, api_key_overrides: Optional[dict] = None, base_url: Optional[str] = None, base_url_overrides: Optional[dict] = None) -> str:
    if not provider or provider == "auto":
        provider = auto_pick_provider(api_key_overrides)
    if provider == "mock":
        return "（本地规则模式无法批改，请配置 AI Key 后重试）"
    try:
        b = (base_url_overrides or {}).get(provider) if isinstance(base_url_overrides, dict) else None
        return _chat(
            provider,
            "你是阅卷教师。批改学生答案：判断对错、给出得分要点与解析。",
            f"题目：{question}\n学生答案：{answer}",
            api_key=api_key,
            base_url=b or base_url,
        )
    except Exception as e:
        return f"（{humanize_error(provider, e)}）自动批改暂不可用。"


# ---------- 答疑 ----------
def chat_reply(message: str, provider: str = "deepseek", api_key: Optional[str] = None, base_url: Optional[str] = None) -> str:
    """按 provider 路由：mock 走本地规则；其他优先用请求密钥，缺 Key / 异常则降级并写明原因。
    可选 base_url：覆盖默认 base（前端用户在 API Key 设置里填的）。"""
    if provider == "mock":
        return _fallback(message, "mock")
    # 区分"未配置 Key"和"调用失败"
    cli = _llm(provider, api_key, base_url)
    if cli is None:
        return _fallback(message, provider, error_reason=None)  # None → 文案: "暂未配置 API Key"
    try:
        return _chat(
            provider,
            "你是 Recall AI 答疑助手，面向高中/大学生，讲题清晰分步，必要时给出变式题巩固。",
            message,
            temperature=0.6,
            max_tokens=1000,
            api_key=api_key,
            base_url=base_url,
        )
    except Exception as e:
        # 调用失败 → 透传原因到降级文案
        return _fallback(message, provider, error_reason=humanize_error(provider, e))


def chat_reply_stream(message: str, provider: str = "deepseek", api_key: Optional[str] = None, base_url: Optional[str] = None):
    """流式答疑：yield 文本分片（token）。用于 /chat/stream 端点，满足 PRD 首字 < 2s。

    - mock / 无 Key / 异常：一次性 yield 降级规则文本（前端当作一段渲染）。
    - 正常：按 OpenAI SSE 流式逐 token 输出，前端边收边渲染。
    """
    system = "你是 Recall AI 答疑助手，面向高中/大学生，讲题清晰分步，必要时给出变式题巩固。"
    if provider == "mock":
        yield _fallback(message, "mock")
        return
    cli = _llm(provider, api_key, base_url)
    if cli is None:
        yield _fallback(message, provider, error_reason=None)
        return
    client, model = cli
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": message}],
            temperature=0.6,
            max_tokens=1000,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        yield _fallback(message, provider, error_reason=humanize_error(provider, e))
