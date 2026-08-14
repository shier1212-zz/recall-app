<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import MistakeCard from '../components/MistakeCard.vue'
import { exportPdf } from '../api'
import { SUBJECTS, SUBJECT_COLORS, computeSubjectStats } from '../utils/subjects'

const router = useRouter()
const activeSubject = ref('')            // '' = 全部
const query = ref('')
const filter = ref<'all' | 'reviewed' | 'todo'>('all')

/** 每个学科的错题数（共享同一份标准与"其它"聚合，让错题集侧边栏与数据面板显示一致） */
const subjectStats = computed(() => computeSubjectStats(store.mistakes))

const list = computed(() =>
  store.mistakes.filter(m => {
    if (activeSubject.value && m.subject !== activeSubject.value) return false
    if (filter.value === 'reviewed' && !m.reviewed) return false
    if (filter.value === 'todo' && m.reviewed) return false
    const q = query.value.trim().toLowerCase()
    if (q) {
      const hit =
        m.content.toLowerCase().includes(q) ||
        m.subject.includes(q) ||
        m.knowledgePoints.some(k => k.includes(q))
      if (!hit) return false
    }
    return true
  })
)

/** 点学科；再点同一项则取消；点"全部"亦可重置。 */
function pickSubject(s: string) {
  activeSubject.value = activeSubject.value === s ? '' : s
}
function pickAll() {
  activeSubject.value = ''
}

// F10：分页（前端分片，兼容 1 万+ 题内存渲染）
const pageSize = 12
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(list.value.length / pageSize)))
const pagedList = computed(() => list.value.slice((page.value - 1) * pageSize, page.value * pageSize))
watch([list, activeSubject, filter, query], () => { page.value = 1 })

async function doExport() {
  await exportPdf()
  store.showToast('已导出 PDF 报告')
}

/** 触发批量重跑：仅重跑 provider==''/='mock' 或 ai_status==='fallback' 的错题。
 *  串行执行；进度由 store.batchReparse 内部 toast 反馈。 */
const batchReparseRunning = ref(false)
async function batchReparse() {
  if (batchReparseRunning.value) return
  batchReparseRunning.value = true
  try {
    await store.batchReparse()
  } finally {
    batchReparseRunning.value = false
  }
}

/** 顶部"批量重跑"按钮要显示的待重跑数量（=降级/无 provider 的题数）。 */
const reparseCount = computed(() =>
  store.mistakes.filter(m => !m.provider || m.provider === 'mock' || m.aiStatus === 'fallback').length
)

/** 当前筛选/分类下"未复习"的题数（用于按钮文案 + 禁用态） */
const todoCount = computed(() => list.value.filter(m => !m.reviewed).length)

function startReview() {
  const queue = list.value.filter(m => !m.reviewed)
  if (!queue.length) {
    store.showToast('当前筛选下暂无未复习题目')
    return
  }
  store.startReview(queue)
  router.push('/review')
}
</script>

<template>
  <div class="flex flex-col lg:flex-row gap-6 items-start">
    <!-- 左：错题分类 -->
    <aside class="w-full lg:w-[240px] lg:flex-shrink-0 border border-line rounded-card bg-surface p-4 lg:sticky lg:top-[72px]">
      <!-- 按学科（与录入页"学科"按钮一一对应，是主导航） -->
      <div class="text-cap text-muted mb-3">按学科</div>
      <div
        class="flex items-center justify-between px-2.5 py-2 rounded-ctrl cursor-pointer text-body transition"
        :class="activeSubject === '' ? 'bg-cblue/10 text-qblue font-semibold' : 'hover:bg-bg'"
        @click="pickAll"
      >
        <span class="flex items-center gap-2">📚 全部</span>
        <span class="text-cap text-muted">{{ subjectStats.total }}</span>
      </div>
      <div
        v-for="(s, i) in SUBJECTS" :key="s"
        class="flex items-center justify-between px-2.5 py-2 rounded-ctrl cursor-pointer text-body transition"
        :class="activeSubject === s ? 'bg-cblue/10 text-qblue font-semibold' : 'hover:bg-bg'"
        @click="pickSubject(s)"
      >
        <span class="flex items-center gap-2">
          <i class="w-2 h-2 rounded-full inline-block" :style="{ background: SUBJECT_COLORS[s] }"></i>{{ s }}
        </span>
        <span class="text-cap text-muted">{{ subjectStats.items[i]?.count ?? 0 }}</span>
      </div>
      <!-- 2026-08-15：移除「其它」导航项，只保留 9 个标准学科 -->
    </aside>

    <!-- 右：操作栏 + 卡片列表 -->
    <div class="flex-1 min-w-0 w-full">
      <div class="flex flex-wrap items-center gap-2 mb-6">
        <button class="border border-line bg-surface rounded-ctrl px-3.5 py-2 text-body hover:border-qblue transition" @click="doExport">导出</button>
        <button class="bg-qblue text-white rounded-ctrl px-3.5 py-2 text-body hover:opacity-90 transition" @click="store.openEntry()">＋ 录入</button>
        <button
          class="bg-cgreen text-white rounded-ctrl px-3.5 py-2 text-body hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="todoCount === 0"
          @click="startReview"
        >{{ todoCount === 0 ? '暂无未复习' : `开始复习 (${todoCount})` }}</button>
        <button
          class="border rounded-ctrl px-3.5 py-2 text-body transition flex items-center gap-1"
          :class="batchReparseRunning || reparseCount === 0
            ? 'border-line text-muted cursor-not-allowed'
            : 'border-agreen/40 text-agreen hover:bg-agreen hover:text-surface'"
          :disabled="batchReparseRunning || reparseCount === 0"
          :title="reparseCount === 0 ? '当前没有需要重跑的错题' : '用浏览器中已配置的真实 AI Key 批量重跑所有降级解析的错题'"
          @click="batchReparse"
        >
          <span v-if="!batchReparseRunning">🔄 批量重跑 AI 解析 ({{ reparseCount }})</span>
          <span v-else>⏳ 批量重跑中…</span>
        </button>
        <input
          v-model="query" placeholder="搜索错题、知识点…"
          class="flex-1 min-w-[160px] border border-line rounded-ctrl px-3 py-2 text-body focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
        />
        <div class="flex items-center gap-1 border border-line rounded-ctrl bg-surface p-1">
          <button
            v-for="f in [['all','全部'],['reviewed','已复习'],['todo','未复习']] as const" :key="f[0]"
            class="text-cap px-2.5 py-1 rounded-ctrl transition"
            :class="filter === f[0] ? 'bg-qblue text-white' : 'text-body hover:bg-bg'"
            @click="filter = f[0]"
          >{{ f[1] }}</button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <MistakeCard v-for="m in pagedList" :key="m.id" :mistake="m" />
      </div>
      <div v-if="!list.length" class="text-center text-muted py-20 border border-dashed border-line rounded-card">
        <p class="text-3xl mb-3">📭</p>
        <p>暂无符合条件的错题，点击右上角「＋ 录入」开始收集第一道错题吧</p>
      </div>

      <!-- 分页（F10） -->
      <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 mt-6">
        <button
          class="border border-line rounded-ctrl px-3 py-1.5 text-cap hover:border-qblue transition disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="page === 1" @click="page = page - 1"
        >上一页</button>
        <span class="text-cap text-body">第 {{ page }} / {{ totalPages }} 页 · 共 {{ list.length }} 题</span>
        <button
          class="border border-line rounded-ctrl px-3 py-1.5 text-cap hover:border-qblue transition disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="page === totalPages" @click="page = page + 1"
        >下一页</button>
      </div>
    </div>
  </div>
</template>
