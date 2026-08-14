<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { store } from '../store'
import { ocrUpload } from '../api'

const router = useRouter()
const tab = ref<'photo' | 'shot' | 'text' | 'chat'>('photo')
const text = ref('')
const subject = ref('')                 // 默认空，等待 AI 实时识别
const kps = ref('')
const source = ref('手动录入')
const msg = ref('')
const uploading = ref(false)
const classifying = ref(false)          // 学科识别 loading
const classifyReason = ref('')          // 识别失败/降级原因（用于提示）
const aiSubject = ref(false)            // 当前学科是否由 AI 给出（true → 用户没手动改过）
const categoryId = ref<number>(1)

const subjects = ['数学', '物理', '英语', '化学', '生物', '历史', '政治', '地理', '语文', '信息']

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

// 学科识别：录入时实时调用 AI（debounced 800ms，避免每次按键都打 API）
let classifyTimer: number | null = null
function scheduleClassify(textContent: string) {
  if (classifyTimer) window.clearTimeout(classifyTimer)
  const c = (textContent || '').trim()
  // 太短不调（< 4 个有效字符，避免噪声请求）；但只要内容变化就清掉旧值，避免残留旧学科
  if (c.length < 4) {
    classifyReason.value = c ? '题目太短，请补全后再识别' : ''
    classifying.value = false
    return
  }
  classifyTimer = window.setTimeout(async () => {
    classifying.value = true
    try {
      const r = await store.classifySubject(c)
      // 只在"AI 仍是主来源"时覆盖；用户手动选了学科后不再回写
      if (aiSubject.value) {
        if (r.subject && r.subject !== '未分类') {
          subject.value = r.subject
        }
        // 知识点也顺手回填（仅当用户没填）
        if (r.knowledgePoints && r.knowledgePoints.length && !kps.value.trim()) {
          kps.value = r.knowledgePoints.join('、')
        }
      }
      classifyReason.value = r.aiStatus === 'fallback' ? (r.reason || 'AI 识别失败，请手动选择学科') : ''
    } finally {
      classifying.value = false
    }
  }, 800)
}

// 文本 tab：题目内容变化时触发学科识别
watch(text, (v) => scheduleClassify(v))
// 对话 tab：口述内容变化时触发
watch(msg, (v) => scheduleClassify(v))

// 用户手动点击学科按钮时：标记为非 AI 来源，AI 不再覆盖
function pickSubjectManually(s: string) {
  subject.value = s
  aiSubject.value = false
  classifyReason.value = ''
}

async function submit() {
  if (!text.value.trim()) { store.showToast('请先填写题目内容'); return }
  // 若 AI 还没识别或识别失败，主动再调一次以确保学科合理
  if (!subject.value.trim() || subject.value === '未分类') {
    classifying.value = true
    try {
      const r = await store.classifySubject(text.value.trim())
      if (r.subject && r.subject !== '未分类') subject.value = r.subject
      if (r.knowledgePoints?.length && !kps.value.trim()) kps.value = r.knowledgePoints.join('、')
    } finally {
      classifying.value = false
    }
  }
  await store.addMistake({
    content: text.value.trim(),
    subject: subject.value,
    knowledgePoints: kps.value.split(/[,，\/\s]+/).filter(Boolean),
    source: source.value || '手动录入',
    categoryId: categoryId.value,
  })
  text.value = ''; kps.value = ''; subject.value = ''; aiSubject.value = false; classifyReason.value = ''
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
      // OCR 后清掉旧的学科标记，让 watch(text) → scheduleClassify → AI 重新识别
      subject.value = ''
      aiSubject.value = true
      classifyReason.value = ''
      store.showToast('OCR 识别完成，AI 正在识别学科…')
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

async function archiveFromChat() {
  if (!msg.value.trim()) { store.showToast('请先描述你的错题'); return }
  // 对话归档前再次确认学科（与 submit 同样的兜底）
  if (!subject.value.trim() || subject.value === '未分类') {
    classifying.value = true
    try {
      const r = await store.classifySubject(msg.value.trim())
      if (r.subject && r.subject !== '未分类') subject.value = r.subject
    } finally {
      classifying.value = false
    }
  }
  await store.addMistake({
    content: msg.value.trim(),
    subject: subject.value,
    knowledgePoints: kps.value.split(/[,，\/\s]+/).filter(Boolean),
    source: '对话录入',
    categoryId: categoryId.value,
  })
  msg.value = ''; subject.value = ''; aiSubject.value = false; classifyReason.value = ''
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
        <div class="flex items-center gap-2 my-3">
          <span class="text-cap text-muted whitespace-nowrap">学科</span>
          <span v-if="classifying" class="text-cap text-qblue animate-pulse">AI 识别中…</span>
          <span v-else-if="subject && aiSubject" class="text-cap text-qblue">✨ AI 已识别</span>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="s in subjects" :key="s"
            class="text-cap border border-dashed rounded-tag px-2 py-0.5 transition"
            :class="subject === s ? 'bg-qblue text-white border-qblue' : 'border-line text-body hover:border-qblue'"
            @click="pickSubjectManually(s)"
          >{{ s }}</button>
        </div>
        <p v-if="classifyReason" class="text-cap text-warn mt-2">⚠️ {{ classifyReason }}</p>
        <input
          v-model="kps" placeholder="知识点（可选，AI 识别后会自动补充）"
          class="w-full border border-line rounded-ctrl px-3 py-2 text-body mt-2 focus:outline-none focus:border-qblue"
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
        <div class="flex items-center gap-2 mt-3">
          <span class="text-cap text-muted whitespace-nowrap">学科</span>
          <span v-if="classifying" class="text-cap text-qblue animate-pulse">AI 识别中…</span>
          <span v-else-if="subject && aiSubject" class="text-cap text-qblue">✨ {{ subject || '待识别' }}</span>
          <span v-else-if="subject" class="text-cap text-body">{{ subject }}</span>
        </div>
        <p v-if="classifyReason" class="text-cap text-warn mt-1">⚠️ {{ classifyReason }}</p>
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