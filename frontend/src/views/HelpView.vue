<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
const faqs = [
  {
    q: '如何录入错题？',
    a: '点击「＋ 录入」，支持拍照、截图、文本、对话四种方式，AI 自动识别学科、知识点与错因并归档到对应错题本。'
  },
  {
    q: '复习计划是怎么生成的？',
    a: '基于 SM-2 遗忘曲线算法，根据每道题的掌握度与历史复习次数自动排程复习任务（已掌握 → 间隔延长，未掌握 → 次日重练）。'
  },
  {
    q: '变式题从哪来？',
    a: 'AI 针对错题知识点生成同考点变式题，并自动批改、回写掌握度。'
  },
  {
    q: '数据能导出吗？',
    a: '支持一键导出 PDF 学习报告（在「错题集」点「导出」）与 Markdown 错题清单（ReportLab / 文本生成）。'
  }
]

function gotoChat() {
  router.push('/chat')
}
</script>

<template>
  <div>
    <h2 class="text-h2 mb-6">帮助中心</h2>
    <div class="space-y-3 max-w-3xl">
      <details v-for="f in faqs" :key="f.q" class="bg-surface border border-line rounded-card p-4 open:border-qblue/40">
        <summary class="cursor-pointer text-body font-semibold flex justify-between items-center">{{ f.q }}<span class="text-muted">▸</span></summary>
        <p class="mt-3 text-body text-body">{{ f.a }}</p>
      </details>
    </div>
    <div class="mt-8 max-w-3xl border border-dashed border-line rounded-card p-6 text-center text-body">
      仍有疑问？可前往<span class="text-qblue cursor-pointer" @click="gotoChat">「AI 答疑」直接提问</span>。
    </div>
  </div>
</template>
