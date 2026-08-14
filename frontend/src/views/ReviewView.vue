<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import type { ReviewResult } from '../types'
import { formatAiAnalysis } from '../utils/formatAi'

const router = useRouter()
const showAnalysis = ref(false)
// 用户在复习时手敲的答案：仅本会话有效，切到下一题自动清空，**不持久化、不参与比对**
const myAnswer = ref('')

const queue = computed(() => store.reviewQueue)
const total = computed(() => queue.value.length)
const done = computed(() => store.reviewDone)
const current = computed(() => (done.value || total.value === 0 ? null : queue.value[store.reviewIndex]))
const progress = computed(() => (total.value === 0 ? 0 : Math.round((store.reviewIndex / total.value) * 100)))
const stats = computed(() => store.reviewStats)
// 本次复习过的题目数（已通过 recordReview 即时落库的题）
const reviewedCount = computed(() => stats.value.mastered + stats.value.unmastered + stats.value.skipped)

/** 历史脏数据/双重 JSON/替代符等异常 → 经 formatAiAnalysis 规范化为可读纯文本 */
const formattedAnalysis = computed(() => (current.value ? formatAiAnalysis(current.value.aiAnalysis) : ''))

// 切到下一题时清空作答区，让用户对当前题专心作答
watch(
  () => current.value?.id,
  () => { myAnswer.value = '' }
)

async function act(result: ReviewResult) {
  if (!current.value) return
  const ok = await store.recordReview(current.value.id, result)
  if (!ok) return
  showAnalysis.value = false
  // 切下一题——myAnswer 会被 watch 清空
  store.advanceReview()
}

// 题目态底部的「退出复习」按钮：
// recordReview 已经在用户每次按 还不太会/跳过/我已掌握 时即时把单题结果写到后端，
// 所以点退出不需要再次批量保存——只要清掉本地 session 状态并回到错题集页。
// toast 反馈"已保存 N 道题"让用户明确知道复习进度不会丢。
function exitToMistakeBook() {
  const saved = reviewedCount.value
  store.exitReview()
  if (saved > 0) store.showToast(`已保存本次复习的 ${saved} 道题`)
  router.push('/')
}

// 顶部"← 退出复习"按钮：仍保留 confirm 兜底（防止误点）；语义与底部按钮一致：已复习的题不丢
function askExit() {
  if (total.value > 0 && !done.value) {
    if (!confirm('退出后已复习过的题目仍会保留，未点击操作的题目将回到队列。确定要退出吗？')) return
  }
  exitToMistakeBook()
}

function restartUnmastered() {
  store.restartUnmasteredRound()
}
</script>

<template>
  <div class="max-w-[820px] mx-auto">
    <!-- 顶部：退出 / 进度 / 占位 -->
    <div class="flex items-center justify-between mb-5">
      <button class="text-cap text-body hover:text-ink transition flex items-center gap-1" @click="askExit">
        <span>←</span><span>退出复习</span>
      </button>
      <div v-if="!done && total > 0" class="text-cap text-body">
        第 <span class="text-ink font-semibold text-body">{{ store.reviewIndex + 1 }}</span> / {{ total }} 题
      </div>
      <div v-else-if="done" class="text-cap text-body">已完成本次复习</div>
      <div v-else class="text-cap text-body">无未复习题目</div>
      <div class="w-16"></div>
    </div>

    <!-- 进度条 -->
    <div v-if="!done && total > 0" class="h-1.5 bg-bg rounded-full overflow-hidden mb-8">
      <div class="h-full bg-cgreen transition-all duration-300" :style="{ width: progress + '%' }"></div>
    </div>

    <!-- 题目卡片（逐题模式） -->
    <div v-if="!done && current" class="bg-surface border border-line rounded-card p-6 lg:p-8 mb-6 shadow-card">
      <div class="flex items-center gap-2 mb-3 flex-wrap">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-cap bg-qblue/10 text-qblue font-semibold">
          {{ current.subject || '未分类' }}
        </span>
        <span v-if="current.reviewCount > 0" class="text-cap text-muted">
          已复习 {{ current.reviewCount }} 次
        </span>
        <span v-if="current.source" class="text-cap text-muted">
          · 来源：{{ current.source }}
        </span>
      </div>

      <h2 class="text-h2 font-semibold mb-4" style="line-height: 1.6">
        {{ current.content }}
      </h2>

      <div v-if="current.knowledgePoints && current.knowledgePoints.length" class="flex flex-wrap gap-1.5 mb-5">
        <span
          v-for="k in current.knowledgePoints" :key="k"
          class="text-cap px-2 py-0.5 border border-line rounded-ctrl text-muted"
        >
          # {{ k }}
        </span>
      </div>

      <!-- AI 解析（折叠） -->
      <div class="border-t border-line pt-4">
        <button
          class="flex items-center justify-between w-full text-cap text-body hover:text-ink transition"
          @click="showAnalysis = !showAnalysis"
        >
          <span class="flex items-center gap-1.5">
            <span class="text-cgreen">✦</span>
            <span class="font-semibold">AI 解析</span>
          </span>
          <span class="text-muted">{{ showAnalysis ? '收起 ▴' : '展开 ▾' }}</span>
        </button>
        <div
          v-if="showAnalysis"
          class="mt-3 p-3 bg-cgreen/5 border border-cgreen/30 rounded-ctrl text-body"
          style="color: #065F46; line-height: 1.7"
        >
          {{ formattedAnalysis || '暂无 AI 解析。' }}
        </div>
      </div>

      <!-- 我的作答（仅本会话保存，切到下一题自动清空，不与正确答案比对） -->
      <div class="border-t border-line pt-4 mt-4">
        <label class="block">
          <span class="text-cap text-body font-semibold mb-1.5 block">📝 我的作答</span>
          <textarea
            v-model="myAnswer"
            rows="4"
            placeholder="在这里写下你的思路或答案（仅供本次复习回顾，不会与正确答案比对，也不会保存到错题集）"
            class="w-full border border-line rounded-ctrl p-3 text-body resize-y min-h-[88px] focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
          />
        </label>
      </div>
    </div>

    <!-- 操作按钮（仅题目态显示） -->
    <div v-if="!done && current" class="grid grid-cols-3 gap-3">
      <button
        class="border border-warning bg-surface rounded-card py-3 text-warning font-semibold hover:bg-warning/10 transition flex flex-col items-center gap-1"
        @click="act('unmastered')"
      >
        <span class="text-xl">😅</span><span class="text-body">还不太会</span>
      </button>
      <button
        class="border border-line bg-surface text-body rounded-card py-3 font-semibold hover:border-ink hover:text-ink transition flex flex-col items-center gap-1"
        @click="act('skip')"
      >
        <span class="text-xl">⏭️</span><span class="text-body">跳过</span>
      </button>
      <button
        class="bg-success text-white rounded-card py-3 font-semibold hover:opacity-90 transition flex flex-col items-center gap-1 shadow-card"
        @click="act('mastered')"
      >
        <span class="text-xl">✅</span><span class="text-body">我已掌握</span>
      </button>
    </div>

    <!-- 退出复习（题目态底部独立按钮，保存已复习过的题并回到错题集） -->
    <div v-if="!done && current" class="mt-4 flex justify-center">
      <button
        class="text-cap text-muted hover:text-ink transition flex items-center gap-1.5 px-4 py-2 rounded-ctrl hover:bg-bg"
        :title="reviewedCount > 0 ? `已保存 ${reviewedCount} 道题，点击退出并回到错题集` : '退出复习并回到错题集'"
        @click="exitToMistakeBook"
      >
        <span>←</span>
        <span>退出复习</span>
        <span v-if="reviewedCount > 0" class="text-cap text-qblue ml-1">（已保存 {{ reviewedCount }} 道）</span>
      </button>
    </div>

    <!-- 结算页 -->
    <div v-if="done" class="bg-surface border border-line rounded-card p-8 text-center shadow-card">
      <div class="text-5xl mb-3">🎉</div>
      <h2 class="text-h2 font-semibold mb-2">已完成本次复习</h2>
      <p class="text-body text-muted mb-6">本次共复习 {{ total }} 道错题</p>
      <div class="grid grid-cols-3 gap-3 max-w-[480px] mx-auto mb-6">
        <div class="border border-line rounded-card py-4">
          <div class="text-h2 text-success font-bold">{{ stats.mastered }}</div>
          <div class="text-cap text-muted mt-1">已掌握</div>
        </div>
        <div class="border border-line rounded-card py-4">
          <div class="text-h2 text-warning font-bold">{{ stats.unmastered }}</div>
          <div class="text-cap text-muted mt-1">还不太会</div>
        </div>
        <div class="border border-line rounded-card py-4">
          <div class="text-h2 text-muted font-bold">{{ stats.skipped }}</div>
          <div class="text-cap text-muted mt-1">跳过</div>
        </div>
      </div>
      <div class="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          v-if="stats.unmastered > 0"
          class="border border-qblue text-qblue rounded-ctrl px-5 py-2.5 text-body font-semibold hover:bg-qblue/5 transition"
          @click="restartUnmastered"
        >再来一轮未掌握（{{ stats.unmastered }}）</button>
        <button
          class="bg-qblue text-white rounded-ctrl px-5 py-2.5 text-body font-semibold hover:opacity-90 transition"
          @click="askExit"
        >回到错题本</button>
      </div>
    </div>

    <!-- 队列为空（没题可复习） -->
    <div v-if="!done && total === 0" class="text-center py-20">
      <div class="text-5xl mb-3">🎯</div>
      <h2 class="text-h2 font-semibold mb-2">暂无未复习题目</h2>
      <p class="text-body text-muted mb-6">所有错题都已复习，继续保持！</p>
      <button
        class="bg-qblue text-white rounded-ctrl px-5 py-2.5 text-body font-semibold hover:opacity-90 transition"
        @click="askExit"
      >回到错题本</button>
    </div>
  </div>
</template>
