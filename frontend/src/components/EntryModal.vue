<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import { ocrUpload } from '../api'

const router = useRouter()
const tab = ref<'photo' | 'shot' | 'text' | 'chat'>('photo')
const text = ref('')
const subject = ref('数学')
const kps = ref('')
const source = ref('手动录入')
const msg = ref('')
const uploading = ref(false)
const categoryId = ref<number>(1)

const subjects = ['数学', '物理', '英语', '化学', '生物', '历史', '政治', '地理']

const tabs = [
  { key: 'photo' as const, label: '📷 拍照' },
  { key: 'shot' as const, label: '✂️ 截图' },
  { key: 'text' as const, label: '📝 文本' },
  { key: 'chat' as const, label: '💬 对话' }
]

// 默认选中第一个错题本
watch(
  () => store.categories,
  (cats) => {
    if (cats.length && !cats.find(c => c.id === categoryId.value)) categoryId.value = cats[0].id
  },
  { immediate: true }
)

async function submit() {
  if (!text.value.trim()) { store.showToast('请先填写题目内容'); return }
  await store.addMistake({
    content: text.value.trim(),
    subject: subject.value,
    knowledgePoints: kps.value.split(/[,，\/\s]+/).filter(Boolean),
    source: source.value || '手动录入',
    categoryId: categoryId.value,
  })
  text.value = ''; kps.value = ''
  store.closeEntry()
}

async function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (!f) return
  uploading.value = true
  try {
    const res = await ocrUpload(f)
    tab.value = 'text'  // F1：无论成功与否都切到文本 tab，让用户看到/补充题目
    if (res.text && res.text.trim()) {
      text.value = res.text
      if (res.subject) subject.value = res.subject
      store.showToast('OCR 识别完成，请确认题目内容')
    } else {
      store.showToast('未能识别到文字，请手动输入题目')
    }
  } catch (err) {
    tab.value = 'text'  // F1：识别失败也切到文本 tab，避免流程中断
    store.showToast('OCR 识别失败（依赖未安装），请手动输入题目')
  } finally {
    uploading.value = false
    input.value = ''  // 允许重复选择同一文件
  }
}

function archiveFromChat() {
  if (!msg.value.trim()) { store.showToast('请先描述你的错题'); return }
  store.addMistake({
    content: msg.value.trim(),
    subject: '',
    knowledgePoints: [],
    source: '对话录入',
    categoryId: categoryId.value,
  })
  msg.value = ''
  store.closeEntry()
}

function gotoChat() {
  store.closeEntry()
  router.push('/chat')
}
</script>

<template>
  <div class="fixed inset-0 z-[70] bg-ink/40 flex items-center justify-center p-4" @click.self="store.closeEntry()">
    <div class="w-full max-w-[560px] bg-surface rounded-card p-8 relative max-h-[90vh] overflow-y-auto">
      <button class="absolute top-4 right-4 text-muted hover:text-ink text-lg" @click="store.closeEntry()">✕</button>
      <h2 class="text-h2">录入错题</h2>
      <p class="text-cap text-body mt-1">选择一种方式，AI 将自动识别学科、知识点与错因并归档。</p>

      <div class="flex gap-2 flex-wrap mt-6">
        <button
          v-for="t in tabs" :key="t.key"
          class="flex-1 min-w-[110px] border rounded-ctrl px-2 py-2.5 text-body transition"
          :class="tab === t.key ? 'border-qblue bg-cblue/10 text-qblue font-semibold' : 'border-line hover:border-qblue'"
          @click="tab = t.key"
        >{{ t.label }}</button>
      </div>

      <!-- 拍照 -->
      <div v-if="tab === 'photo'" class="mt-4 border border-line rounded-card p-6 text-center">
        <p class="text-body text-body">📷 取景框</p>
        <p class="text-cap text-muted mt-1">OCR 自动提取题目文本（若未安装识别依赖，可手动输入）</p>
        <label class="inline-block mt-4 bg-qblue text-white rounded-ctrl px-4 py-2 text-body cursor-pointer hover:opacity-90 transition">
          {{ uploading ? '识别中…' : '拍照 / 相册' }}
          <input type="file" accept="image/*" class="hidden" @change="onFile" />
        </label>
      </div>

      <!-- 截图 -->
      <div v-if="tab === 'shot'" class="mt-4 border border-dashed border-line rounded-card p-6 text-center">
        <p class="text-body text-body">✂️ 拖拽截图到此处，或粘贴（Ctrl+V）</p>
        <p class="text-cap text-muted mt-1">OCR 自动提取题目文本</p>
        <label class="inline-block mt-4 border border-line rounded-ctrl px-4 py-2 text-body cursor-pointer hover:border-qblue transition">
          选择截图
          <input type="file" accept="image/*" class="hidden" @change="onFile" />
        </label>
      </div>

      <!-- 文本 -->
      <div v-if="tab === 'text'" class="mt-4">
        <textarea
          v-model="text" placeholder="粘贴或输入题目内容…"
          class="w-full border border-line rounded-ctrl p-3 text-body resize-y min-h-[96px] focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
        />
        <div class="flex flex-wrap gap-2 my-3">
          <button
            v-for="s in subjects" :key="s"
            class="text-cap border border-dashed rounded-tag px-2 py-0.5 transition"
            :class="subject === s ? 'bg-qblue text-white border-qblue' : 'border-line text-body hover:border-qblue'"
            @click="subject = s"
          >{{ s }}</button>
        </div>
        <input
          v-model="kps" placeholder="知识点（可选，逗号分隔）"
          class="w-full border border-line rounded-ctrl px-3 py-2 text-body focus:outline-none focus:border-qblue"
        />
        <div class="flex items-center gap-2 mt-2">
          <label class="text-cap text-muted whitespace-nowrap">错题本</label>
          <select
            v-model.number="categoryId"
            class="flex-1 border border-line rounded-ctrl px-3 py-2 text-body bg-surface focus:outline-none focus:border-qblue"
          >
            <option v-for="c in store.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <input
          v-model="source" placeholder="来源（如：期中月考）"
          class="w-full border border-line rounded-ctrl px-3 py-2 text-body mt-2 focus:outline-none focus:border-qblue"
        />
      </div>

      <!-- 对话 -->
      <div v-if="tab === 'chat'" class="mt-4">
        <p class="text-cap text-body mb-2">口述或粘贴你的错题，AI 将自动识别学科、知识点并归档到所选错题本。</p>
        <textarea
          v-model="msg" placeholder="例如：这道导数题我不会，求 y=x² 在 x=1 处的切线方程…"
          class="w-full border border-line rounded-ctrl p-3 text-body resize-y min-h-[96px] focus:outline-none focus:border-qblue focus:ring-2 focus:ring-qblue/20"
        />
        <div class="flex gap-2 mt-3">
          <button class="bg-qblue text-white rounded-ctrl px-4 py-2 text-body hover:opacity-90 transition" @click="archiveFromChat">AI 识别并归档</button>
          <button class="border border-line rounded-ctrl px-4 py-2 text-body hover:border-qblue transition" @click="gotoChat">去 AI 答疑提问</button>
        </div>
        <p class="text-cap text-muted mt-2">已归档的题目可在「错题集」查看，AI 解析完成后自动加入复习计划。</p>
      </div>

      <div class="flex justify-end gap-2 mt-8">
        <button class="border border-line rounded-ctrl px-4 py-2 text-body hover:border-qblue transition" @click="store.closeEntry()">取消</button>
        <button class="bg-qblue text-white rounded-ctrl px-4 py-2 text-body hover:opacity-90 transition" @click="submit">AI 识别并归档</button>
      </div>
    </div>
  </div>
</template>
