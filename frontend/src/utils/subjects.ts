/**
 * 学科（subject）共享定义
 *
 * 与「录入错题」弹窗 EntryModal.vue 里的 10 个学科按钮保持一致，
 * 作为整张错题视图体系的主分类维度。
 *
 * - SUBJECTS：标准学科列表（按约定顺序显示）
 * - SUBJECT_COLORS：每个学科对应的色点（用于错题集侧边栏、数据面板分布条）
 * - normalizeSubject()：清洗"计算机科学"/"" 等历史脏数据，让它们聚合到「其它」
 * - computeSubjectStats()：基于 store.mistakes 算出每个学科的题数 + 其它 + 总数
 *
 * 不放在视图内、也不放在 store，是为了让 错题集侧边栏 + 数据面板分布 共享同一份语义。
 */

// 标准 9 学科（与 EntryModal 学科按钮的"value"一一对应；2026-08-15 移除「信息」）
export const SUBJECTS = ['数学', '物理', '英语', '化学', '生物', '历史', '政治', '地理', '语文'] as const

// 学科→展示色（与 EntryModal 按钮色系协调）
export const SUBJECT_COLORS: Record<string, string> = {
  数学: '#5E5CE6',
  物理: '#FF9F0A',
  英语: '#FF453A',
  化学: '#30D158',
  生物: '#34C759',
  历史: '#AC8E68',
  政治: '#FF375F',
  地理: '#0A84FF',
  语文: '#BF5AF2'
}

// 标准化：历史脏数据（如"计算机科学"、"HTML ..."、""）→ 都不在标准列表里，最终会落到"其它"
export function normalizeSubject(s?: string | null): string {
  if (!s) return ''
  const t = String(s).trim()
  if ((SUBJECTS as readonly string[]).includes(t)) return t
  return ''
}

export interface SubjectStat {
  subject: string
  count: number
  /** 不在 SUBJECTS 列表里的归到 '其它'；标准学科此字段就是 subject */
  display: string
}

export interface SubjectStats {
  items: SubjectStat[]           // 按 SUBJECTS 顺序列出（其它 放在末尾）
  total: number                  // 全部错题数
  knownTotal: number             // 属于 10 学科的题数（不含其它）
  otherCount: number             // 其它（历史脏学科）的题数
}

/**
 * 基于错题列表算出学科分布。
 * 用法：const stats = computeSubjectStats(store.mistakes)
 *
 * 2026-08-15：移除「其它」聚合项 + 移除「信息」学科后，只统计 9 个标准学科。
 * 不在 SUBJECTS 里的历史脏数据题（如「计算机科学」/ 空 subject 等）会被忽略，不计入任何指标。
 */
export function computeSubjectStats(mistakes: { subject?: string }[]): SubjectStats {
  const counts: Record<string, number> = {}
  for (const s of SUBJECTS) counts[s] = 0
  for (const m of mistakes ?? []) {
    const norm = normalizeSubject(m.subject)
    if (norm) counts[norm]++
    // 非标准学科的题不再聚合到「其它」（用户已删除该分类）
  }

  const items: SubjectStat[] = SUBJECTS.map(s => ({ subject: s, count: counts[s], display: s }))

  return {
    items,
    total: (mistakes ?? []).length,
    knownTotal: SUBJECTS.reduce((a, s) => a + counts[s], 0),
    otherCount: 0
  }
}
