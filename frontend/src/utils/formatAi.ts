/**
 * 清洗/规范化"AI 解析"字符串，让历史脏数据与异常输出都能展示为正常文本。
 *
 * 主要场景：
 *   - 数据库里的 aiAnalysis 是"双重 JSON 化"的字符串：模型输出合法 JSON 但前端某次错误地又
 *     JSON.stringify 了一次，导致 ai_analysis 字段值是 '{ "subject": "...", ... }' 字面量。
 *   - 模型本身未按 JSON 输出，被后端兜底"原文保存"——含 ◆、■、控制字符、Latin 噪声 token。
 *   - 字符污染（连续空行、孤立的 Latin 片段、超长字段等）。
 *
 * 策略：
 *   1. 尝试把字符串当成 JSON 解析一次（处理"双重 JSON 化"）。
 *   2. 解析出的对象若是 {subject, error_reason, ai_analysis} 形态，组装为分段文本。
 *   3. 解析出的 ai_analysis 字段值若仍是 JSON-like 字符串，递归再解一次。
 *   4. 都不像 JSON → 直接走"字符清洗"（去 ◆、去 Latin 噪声、压缩空行、控制字符、首尾空白）。
 *   5. 返回清洗后的可读文本。
 *
 * 使用：formatAiAnalysis(mistake.aiAnalysis)
 */
export function formatAiAnalysis(raw: string | null | undefined): string {
  if (!raw) return ''
  const s = String(raw)
  if (!s.trim()) return ''

  // 1) 试解析 JSON
  const parsed = tryParseJson(s)
  if (parsed && typeof parsed === 'object' && hasAiShape(parsed)) {
    const subj = cleanText(stringOrEmpty(parsed.subject))
    const kps = arrayOrEmpty(parsed.knowledge_points ?? parsed.knowledgePoints).map(kp => cleanText(kp))
    const err = cleanText(stringOrEmpty(parsed.error_reason ?? parsed.errorReason))
    let analysis = stringOrEmpty(parsed.ai_analysis ?? parsed.aiAnalysis)
    // 解析出的 ai_analysis 仍像 JSON 字面量 → 递归再解一次
    if (looksLikeJson(analysis)) {
      const inner = tryParseJson(analysis)
      if (inner && typeof inner === 'object' && hasAiShape(inner)) {
        analysis = stringOrEmpty(inner.ai_analysis ?? inner.aiAnalysis)
      } else {
        analysis = cleanText(analysis)
      }
    } else {
      analysis = cleanText(analysis)
    }
    const blocks: string[] = []
    if (subj) blocks.push(`【学科】${subj}`)
    if (kps.length) blocks.push(`【知识点】${kps.join('、')}`)
    if (err) blocks.push(`【错因】${err}`)
    if (analysis) blocks.push(`【解析】${analysis}`)
    return blocks.join('\n')
  }

  // 2) 非 JSON 形态：纯字符清洗
  return cleanText(s)
}

function tryParseJson(text: string): unknown | null {
  try {
    // 先剥一次 markdown ```json ... ``` 围栏
    const fence = /```(?:json)?\s*([\s\S]*?)\s*```/i.exec(text)
    const candidate = fence ? fence[1] : text
    try {
      return JSON.parse(candidate)
    } catch {
      // 模型可能在合法 JSON 之后又吐了脏文本（◆ / 控制字符 / 西文片段），
      // 直接整体解析会失败。退而求其次：截取从第一个 { 到最后一个 } 的片段再解析。
      const first = candidate.indexOf('{')
      const last = candidate.lastIndexOf('}')
      if (first !== -1 && last !== -1 && last > first) {
        return JSON.parse(candidate.slice(first, last + 1))
      }
      return null
    }
  } catch {
    return null
  }
}

function looksLikeJson(text: string): boolean {
  const t = text.trim()
  return t.startsWith('{') && t.endsWith('}')
}

function hasAiShape(o: any): boolean {
  if (!o || typeof o !== 'object') return false
  // 至少含 ai_analysis/error_reason/knowledge_points/subject 之一
  const keys = ['ai_analysis', 'aiAnalysis', 'error_reason', 'errorReason', 'knowledge_points', 'knowledgePoints', 'subject']
  return keys.some(k => k in o)
}

function stringOrEmpty(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function arrayOrEmpty(v: unknown): string[] {
  return Array.isArray(v) ? v.filter(x => typeof x === 'string' && x.trim()).map(x => String(x)) : []
}

/** 字符清洗：去 ◆■▲▼●◇、去控制字符、Latin Extended 噪声、压缩空行、控制长度。 */
function cleanText(text: string, maxLen = 1500): string {
  if (!text) return ''
  let s = text
  // 替换字符 U+FFFD
  s = s.replace(/\ufffd/g, '')
  // ASCII 控制字符（保留 \n \r \t）
  s = s.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '')
  // 模型替代符 ◆◇■●▲▼
  s = s.replace(/[◆■▲▼●◇]{2,}/g, ' ')
  for (const sym of ['◆', '■', '▲', '▼', '●', '◇']) {
    s = s.split(sym).join('')
  }
  // Latin Extended 噪声：含变音符号（é/á/ñ/ü…）的拉丁词视为乱码插入，整词丢弃。
  // 纯 ASCII 英文术语（GPS/AI/Python 等）不受影响。
  s = s.replace(/[A-Za-z\u00c0-\u024f]*[\u00c0-\u024f][A-Za-z\u00c0-\u024f]*/g, ' ')
  // 连续空白压缩
  s = s.replace(/[ \t]{2,}/g, ' ')
  s = s.replace(/\n{3,}/g, '\n\n')
  s = s.trim()
  // 长度截断
  if (s.length > maxLen) {
    s = s.slice(0, maxLen).trimEnd() + '…'
  }
  return s
}