<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import MistakeCard from '../components/MistakeCard.vue'
import { exportPdf } from '../api'

const router = useRouter()
const activeCat = ref(0)
const query = ref('')
const filter = ref<'all' | 'reviewed' | 'todo'>('all')
const newCat = ref('')

const list = computed(() =>
  store.mistakes.filter(m => {
    if (activeCat.value !== 0 && m.categoryId !== activeCat.value) return false
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

async function addCat() {
  const name = newCat.value.trim()
  if (!name) { store.showToast('请输入错题本名称'); return }
  try {
    await store.addCat(name)
    newCat.value = ''
  } catch {
    // 失败 toast 已在 store.addCat 内提示
  }
}

// F10：分页（前端分片，兼容 1 万+ 题内存渲染）
const pageSize = 12
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(list.value.length / pageSize)))
const pagedList = computed(() => list.value.slice((page.value - 1) * pageSize, page.value * pageSize))
watch([list, activeCat, filter, query], () => { page.value = 1 })

async function doExport() {
  await exportPdf()
  store.showToast('已导出 PDF 报告')
}

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
      <div class="text-cap text-muted mb-3">错题分类</div>
      <div
        v-for="c in store.categories" :key="c.id"
        class="flex items-center justify-between px-2.5 py-2 rounded-ctrl cursor-pointer text-body transition"
        :class="activeCat === c.id ? 'bg-cblue/10 text-qblue font-semibold' : 'hover:bg-bg'"
        @click="activeCat = c.id"
      >
        <span class="flex items-center gap-2">
          <i class="w-2 h-2 rounded-full inline-block" :style="{ background: c.color }"></i>{{ c.name }}
        </span>
        <span class="text-cap text-muted">{{ c.count }}</span>
      </div>
      <div class="flex gap-1.5 mt-4">
        <input
          v-model="newCat" placeholder="新增错题本…" class="flex-1 min-w-0 border border-line rounded-ctrl px-2.5 py-1.5 text-cap focus:outline-none focus:border-qblue"
          @keydown.enter="addCat"
        />
        <button class="border border-line rounded-ctrl px-2.5 py-1.5 text-cap hover:border-qblue hover:text-qblue transition" @click="addCat">＋</button>
      </div>
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
