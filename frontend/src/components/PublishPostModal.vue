<script setup lang="ts">
/**
 * 发布帖子浮窗：标题 + 完整题目 + 博主解答 + 学科 + 昵称。
 */
import { ref } from 'vue'
import { createCommunityPost } from '../api'
import { store } from '../store'

const emit = defineEmits<{ close: []; published: [] }>()

const title = ref('')
const fullText = ref('')
const solution = ref('')
const subject = ref('')
const authorName = ref(localStorage.getItem('recall_display_name') || '我')
const submitting = ref(false)

// 自动从标题前 80 字生成摘要：如果 fullText 也填了，可以反过来用 fullText 摘要
const summary = ref('')

const subjects = ['数学', '物理', '英语', '化学', '生物', '历史', '政治', '地理', '语文']
// 跟 SUBJECTS 共享同一份，但与原题目解耦（不引用 subjects.ts 是为了保持本组件独立可读）

async function onSubmit() {
  if (!title.value.trim()) {
    store.showToast('请填写标题')
    return
  }
  if (!authorName.value.trim()) {
    store.showToast('请填写你的昵称')
    return
  }
  submitting.value = true
  try {
    const t = title.value.trim()
    // 摘要：优先用用户填的；否则用 fullText 的前 80 字符；最后用标题前 80 字符
    let sum = summary.value.trim()
    if (!sum && fullText.value.trim()) sum = fullText.value.trim().slice(0, 80)
    if (!sum) sum = t.slice(0, 80)
    localStorage.setItem('recall_display_name', authorName.value.trim())
    await createCommunityPost({
      title: t,
      summary: sum,
      fullText: fullText.value.trim(),
      solution: solution.value.trim(),
      subject: subject.value,
      authorName: authorName.value.trim(),
    })
    emit('published')
  } catch (e) {
    store.showToast('发布失败：' + (e as Error).message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-[70] bg-ink/40 flex items-start justify-center p-4 overflow-y-auto"
    @click.self="emit('close')"
  >
    <div class="bg-surface rounded-card shadow-card max-w-[680px] w-full my-8 max-h-[calc(100vh-4rem)] overflow-hidden flex flex-col">
      <!-- 头部 -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-line">
        <h2 class="text-h2 font-bold">📮 发布题目到答题圈</h2>
        <button
          class="text-muted hover:text-ink text-2xl leading-none px-2"
          aria-label="关闭"
          @click="emit('close')"
        >×</button>
      </div>

      <div class="overflow-y-auto px-6 py-5 space-y-4">
        <!-- 标题 -->
        <div>
          <label class="text-cap text-muted block mb-1">题目标题<span class="text-warn">*</span></label>
          <input
            v-model="title"
            class="w-full bg-bg border border-line rounded-ctrl px-3 py-2 text-body outline-none focus:border-qblue transition"
            maxlength="60"
            placeholder="如：求大神解析：圆锥曲线离心率"
          />
        </div>

        <!-- 完整题目 -->
        <div>
          <label class="text-cap text-muted block mb-1">完整题目（可选）</label>
          <textarea
            v-model="fullText"
            rows="4"
            class="w-full bg-bg border border-line rounded-ctrl px-3 py-2 text-body outline-none focus:border-qblue transition resize-y"
            placeholder="把题目抄上来 / 描述清楚问题背景"
          />
        </div>

        <!-- 博主答题思路 -->
        <div>
          <label class="text-cap text-muted block mb-1">博主答题思路 / 建议（可选但推荐）</label>
          <textarea
            v-model="solution"
            rows="4"
            class="w-full bg-bg border border-line rounded-ctrl px-3 py-2 text-body outline-none focus:border-qblue transition resize-y"
            placeholder="你自己的解答、关键步骤、知识点、易错点…"
          />
        </div>

        <!-- 摘要 -->
        <div>
          <label class="text-cap text-muted block mb-1">卡片摘要（不填则自动取完整题目或标题前 80 字）</label>
          <input
            v-model="summary"
            class="w-full bg-bg border border-line rounded-ctrl px-3 py-2 text-body outline-none focus:border-qblue transition"
            maxlength="120"
            placeholder="列表卡片显示的一句话摘要…"
          />
        </div>

        <!-- 学科 + 昵称 -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-cap text-muted block mb-1">学科（可选）</label>
            <select
              v-model="subject"
              class="w-full bg-bg border border-line rounded-ctrl px-3 py-2 text-body outline-none focus:border-qblue transition"
            >
              <option value="">未分类</option>
              <option v-for="s in subjects" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>
          <div>
            <label class="text-cap text-muted block mb-1">你的昵称<span class="text-warn">*</span></label>
            <input
              v-model="authorName"
              maxlength="20"
              class="w-full bg-bg border border-line rounded-ctrl px-3 py-2 text-body outline-none focus:border-qblue transition"
              placeholder="我的昵称"
            />
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 px-6 py-4 border-t border-line bg-bg">
        <button class="text-body px-4 py-2 rounded-ctrl hover:bg-line/20 transition" @click="emit('close')">取消</button>
        <button
          class="bg-qblue text-white font-semibold px-5 py-2 rounded-ctrl shadow-card disabled:opacity-50 hover:opacity-90 transition"
          :disabled="submitting || !title.trim() || !authorName.trim()"
          @click="onSubmit"
        >{{ submitting ? '发布中…' : '发布到答题圈' }}</button>
      </div>
    </div>
  </div>
</template>