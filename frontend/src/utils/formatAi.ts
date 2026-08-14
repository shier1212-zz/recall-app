/**
 * 清洗/规范化"AI 解析"字符串，让历史脏数据与异常输出都能展示为正常文本。
 *
 * 主要场景：
 *   - 数据库里的 aiAnalysis 是"双重 JSON 化"的字符串：模型输出合法 JSON 但前端某次错误地又
 *     JSON.stringify 了一次，导致 ai_analysis 字段值是 '{ "subject": "...", ... }' 字面量。
 *   - 模型输出"接近 JSON 但实际损坏"——重复键 / 缺失开头的引号 / 末尾 `}}` 多余闭合 / 后面
 *     还跟一段中文提示。这条路下 strict JSON.parse 与「截取首尾 {}」都会失败，但实际文本里
 *     `subject / error_reason / ai_analysis / knowledge_points` 的字段名都还在。
 *   - 字符污染（◆、■、控制字符、Latin Extended 噪声 token、连续空行等）。
 *
 * 策略：
 *   1. 严格 JSON 解析成功 → 检测 ai_shape → 结构化输出。
 *   2. 失败但文本像 JSON（首字符 { 或内含 ":"）→ 走宽松字段抽取（取最后一次出现的字段值，
 *      状态机走引号/转义，能容忍引号残缺和重复键）。
 *   3. 仍然失败 → 兜底删除 JSON 语法字符（{} ",", :[]）再做字符清洗。
 *   4. 返回清洗后的可读纯文本（【学科】...【解析】... 分段格式）。
 *
 * 使用：formatAiAnalysis(mistake.aiAnalysis)
 */
export function formatAiAnalysis(raw: string | null | undefined): string {
  if (!raw) return ''
  const s = String(raw)
  if (!s.trim()) return ''

  // 1) 严格 JSON 解析
  const strict = tryParseJson(s)
  if (typeof strict === 'string' && strict.trim() && strict !== s) {
    // 字符串被多包了一层 JSON.stringify：递归处理内层
    return formatAiAnalysis(strict)
  }
  if (strict && typeof strict === 'object' && hasAiShape(strict)) {
    return renderStructured(strict)
  }

  // 2) 兜底：宽松字段抽取（处理重复键 / 缺开头引号 / 多余 }} 等损坏 JSON）
  const looksJson = /[{:]/.test(s) && /["']?subject["']?|"ai_analysis"|"error_reason"/.test(s)
  if (looksJson) {
    const loose = extractLooseFields(s)
    if (loose && Object.keys(loose).length) {
      return renderStructured(loose)
    }
  }

  // 3) 实在抽不出来 → 删 JSON 语法字符后再字符清洗
  return cleanText(stripJsonSyntax(s))
}

/** 把已抽取好的字段对象渲染为分段文本。 */
function renderStructured(parsed: any): string {
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
      // 走宽松抽取
      const loose = extractLooseFields(analysis)
      if (loose && loose.ai_analysis) analysis = loose.ai_analysis
      else analysis = cleanText(stripJsonSyntax(analysis))
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

function tryParseJson(text: string): unknown | null {
  try {
    const fence = /```(?:json)?\s*([\s\S]*?)\s*```/i.exec(text)
    const candidate = fence ? fence[1] : text
    try {
      return JSON.parse(candidate)
    } catch {
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

/**
 * 宽松字段抽取：处理「几乎像 JSON 但实际损坏」的文本。
 * - 用正则定位字段名（容忍前后缺引号、重复键——取最后一次匹配）
 * - 状态机读取 value：可带引号或不带，正确处理 \n / \" / \\ 等转义
 * - 数组字段（knowledge_points）特殊处理：用括号配对定位 []
 */
function extractLooseFields(text: string): Record<string, unknown> {
  const out: Record<string, unknown> = {}

  const grabString = (key: string): string => {
    // 匹配 "key": 或 "key":  或 key": 或 'key': （容忍缺失的引号）
    const re = new RegExp(`["']?${escapeRegex(key)}["']?\\s*:\\s*`, 'g')
    let m: RegExpExecArray | null = null
    let lastIdx = -1
    let lastEnd = 0
    let tmp: RegExpExecArray | null
    while ((tmp = re.exec(text)) !== null) {
      lastIdx = tmp.index
      lastEnd = tmp.index + tmp[0].length
      m = tmp
    }
    if (lastIdx < 0 || !m) return ''
    const open = text[lastEnd] // 是否紧跟一个开引号
    if (open !== '"' && open !== "'") {
      // 无引号 value：读到下一个 "key": 或行尾
      const rest = text.slice(lastEnd)
      const endMatch = /\r?\n\s*["']?[a-zA-Z_]\w*["']?\s*:|^[}\]]|\r?\n[})\]]|\Z/.exec(rest)
      const len = endMatch ? endMatch.index : rest.length
      return unescapeString(rest.slice(0, len).trim())
    }
    // 有引号 value：状态机读，遇到匹配闭合引号结束
    const close = open
    let i = lastEnd + 1
    let val = ''
    while (i < text.length) {
      const c = text[i]
      if (c === '\\' && i + 1 < text.length) {
        const next = text[i + 1]
        val += unescapeChar(next)
        i += 2
        continue
      }
      if (c === close) {
        return val
      }
      val += c
      i++
    }
    return val
  }

  const subject = grabString('subject')
  if (subject) out.subject = subject

  const errorReason = grabString('error_reason')
  if (errorReason) out.error_reason = errorReason

  const analysis = grabString('ai_analysis')
  if (analysis) out.ai_analysis = analysis

  // knowledge_points 数组：找 [ 然后括号配对
  const arrRe = /["']?knowledge_points["']?\s*:\s*\[/g
  let arrM: RegExpExecArray | null = null
  let arrLast: RegExpExecArray | null = null
  while ((arrM = arrRe.exec(text)) !== null) arrLast = arrM
  if (arrLast) {
    const start = arrLast.index + arrLast[0].length
    let depth = 1
    let i = start
    while (i < text.length && depth > 0) {
      const c = text[i]
      if (c === '[') depth++
      else if (c === ']') depth--
      i++
    }
    const body = text.slice(start, i - 1)
    const items: string[] = []
    const itemRe = /["']([^"']+)["']/g
    let im: RegExpExecArray | null
    while ((im = itemRe.exec(body)) !== null) items.push(im[1])
    if (items.length) out.knowledge_points = items
  }

  return out
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function unescapeChar(c: string): string {
  if (c === 'n') return '\n'
  if (c === 'r') return '\r'
  if (c === 't') return '\t'
  if (c === '"') return '"'
  if (c === "'") return "'"
  if (c === '\\') return '\\'
  return c
}

function unescapeString(s: string): string {
  return s
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '\r')
    .replace(/\\t/g, '\t')
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")
    .replace(/\\\\/g, '\\')
}

/** 兜底：删 JSON 语法字符（让纯字符洗后输出更可读）。 */
function stripJsonSyntax(s: string): string {
  return s
    .replace(/\{+/g, '')
    .replace(/\}+/g, '')
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")
    .replace(/\\\\/g, '\\')
    .replace(/\\n/g, '\n')
    .replace(/"([a-zA-Z_][\w_-]*?)"\s*:\s*/g, '$1：')  // "key": → key：
    .replace(/"\s*:\s*/g, '：')
    .replace(/^[\s,]+|[\s,]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function hasAiShape(o: any): boolean {
  if (!o || typeof o !== 'object') return false
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
  s = s.replace(/\ufffd/g, '')
  s = s.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '')
  s = s.replace(/[◆■▲▼●◇]{2,}/g, ' ')
  for (const sym of ['◆', '■', '▲', '▼', '●', '◇']) {
    s = s.split(sym).join('')
  }
  s = s.replace(/[A-Za-z\u00c0-\u024f]*[\u00c0-\u024f][A-Za-z\u00c0-\u024f]*/g, ' ')
  s = s.replace(/[ \t]{2,}/g, ' ')
  s = s.replace(/\n{3,}/g, '\n\n')
  s = s.trim()
  if (s.length > maxLen) {
    s = s.slice(0, maxLen).trimEnd() + '…'
  }
  return s
}