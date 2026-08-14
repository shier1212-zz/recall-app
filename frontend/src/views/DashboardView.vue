<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { store } from '../store'
import { fetchOverview } from '../api'
import { computeSubjectStats, SUBJECT_COLORS } from '../utils/subjects'

const overview = ref<{
  total: number; reviewed: number; todo: number; categories: number; due_today: number
  subject_stats: { subject: string; count: number }[]; trend: { date: string; count: number }[]
} | null>(null)

onMounted(async () => {
  try {
    overview.value = await fetchOverview()
  } catch (e) {
    console.error('fetchOverview 失败', e)
  }
})

const total = computed(() => store.mistakes.length)
const mastered = computed(() => store.mistakes.filter(m => m.reviewed).length)
const todo = computed(() => store.mistakes.filter(m => !m.reviewed).length)
const dueToday = computed(() => overview.value?.due_today ?? 0)

/**
 * 学科分布：直接基于本地 store.mistakes 计算（与"错题集"侧边栏共用同一份
 * 10 学科定义 / SUBJECT_COLORS / 「其它」归类）。
 *
 * 不走 /api/analysis/overview 字段，理由：
 *   api.ts 里的 toCamelKeys 拦截器把后端 snake_case 全部转成 camelCase，
 *   导致 overview.subject_stats 在前端始终是 undefined → 一直显示「暂无」。
 * 改用客户端计算后，错题集侧边栏 ↔ 数据面板分布 100% 一致，刷新即同步。
 */
const subjectStats = computed(() => computeSubjectStats(store.mistakes))
const subjectDistMax = computed(() => Math.max(1, ...subjectStats.value.items.map(i => i.count)))

// 趋势 SVG 坐标（基于真实近 7 日录入量）
const trendPoints = computed(() => {
  const t = overview.value?.trend ?? []
  if (!t.length) return ''
  const max = Math.max(1, ...t.map(x => x.count))
  const w = 700, h = 200, padX = 40, padY = 20
  return t.map((x, i) => {
    const xPos = padX + (w - 2 * padX) * (i / Math.max(1, t.length - 1))
    const yPos = h - padY - (h - 2 * padY) * (x.count / max)
    return `${xPos.toFixed(1)},${yPos.toFixed(1)}`
  }).join(' ')
})

</script>

<template>
  <div>
    <h2 class="text-h2 mb-4">学习数据看板</h2>
    <p class="text-cap text-body mb-6">数据来自后端 /api/analysis/overview 实时聚合。</p>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="bg-surface border border-line rounded-card p-4">
        <div class="text-h1 text-qblue">{{ total }}</div><div class="text-cap text-body mt-1">错题总数</div>
      </div>
      <div class="bg-surface border border-line rounded-card p-4">
        <div class="text-h1 text-success">{{ mastered }}</div><div class="text-cap text-body mt-1">已掌握</div>
      </div>
      <div class="bg-surface border border-line rounded-card p-4">
        <div class="text-h1 text-warning">{{ todo }}</div><div class="text-cap text-body mt-1">待复习</div>
      </div>
      <div class="bg-surface border border-line rounded-card p-4">
        <div class="text-h1 text-body">{{ store.categories.length }}</div><div class="text-cap text-body mt-1">错题本数</div>
      </div>
    </div>

    <div class="bg-surface border border-line rounded-card p-6 mb-6">
      <h3 class="text-h2 mb-4">近 7 日录入趋势（真实数据）</h3>
      <svg v-if="trendPoints" viewBox="0 0 700 220" class="w-full h-auto">
        <line x1="40" y1="200" x2="680" y2="200" stroke="var(--line)" />
        <line x1="40" y1="20" x2="40" y2="200" stroke="var(--line)" />
        <polyline :points="trendPoints" fill="none" stroke="var(--q-blue)" stroke-width="3" />
        <template v-for="(x, i) in (overview?.trend ?? [])" :key="i">
          <text :x="40 + 620 * (i / Math.max(1, (overview?.trend.length ?? 1) - 1))" y="215" font-size="11" fill="var(--muted)" text-anchor="middle">{{ x.date.slice(5) }}</text>
        </template>
      </svg>
      <p v-else class="text-cap text-muted">暂无趋势数据</p>
      <div class="flex gap-4 mt-3 text-cap text-body">
        <span><i class="inline-block w-3 h-1 rounded mr-1" style="background:var(--q-blue)"></i>每日录入量</span>
        <span v-if="dueToday" class="text-warning">今日应复习：{{ dueToday }} 题</span>
      </div>
    </div>

    <div class="bg-surface border border-line rounded-card p-6">
      <div class="flex items-baseline justify-between mb-4">
        <h3 class="text-h2">学科分布</h3>
        <span class="text-cap text-muted">
          共 <span class="text-qblue font-semibold">{{ subjectStats.total }}</span> 题
        </span>
      </div>
      <div v-if="subjectStats.items.length" class="space-y-3">
        <div v-for="s in subjectStats.items" :key="s.subject" class="flex items-center gap-3">
          <span class="text-body w-20 shrink-0 flex items-center gap-1.5">
            <i
              v-if="s.subject !== '__other__'"
              class="w-2 h-2 rounded-full inline-block"
              :style="{ background: SUBJECT_COLORS[s.subject] }"
            ></i>
            <i v-else class="w-2 h-2 rounded-full inline-block bg-muted"></i>
            {{ s.display }}
          </span>
          <div class="flex-1 h-3 bg-bg rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all"
              :style="{
                width: (s.count / subjectDistMax * 100) + '%',
                background: s.subject === '__other__' ? 'var(--muted)' : SUBJECT_COLORS[s.subject]
              }"
            ></div>
          </div>
          <span class="text-cap text-muted w-10 text-right tabular-nums">{{ s.count }}</span>
        </div>
      </div>
      <p v-else class="text-cap text-muted">暂无学科分布数据</p>
      <p v-if="subjectStats.total === 0 && store.mistakes.length === 0" class="text-cap text-muted">请先录入错题</p>
    </div>
  </div>
</template>
