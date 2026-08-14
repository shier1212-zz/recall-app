<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import TopNav from './components/TopNav.vue'
import EntryModal from './components/EntryModal.vue'
import { store } from './store'

const route = useRoute()
const active = computed(() => route.name as string)

const navItems = [
  { to: '/', name: 'home', label: '错题集', icon: '📚' },
  { to: '/ai', name: 'ai', label: 'AI 答疑', icon: '💬' },
  { to: '/posts', name: 'posts', label: '答题圈', icon: '📮' },
  { to: '/dashboard', name: 'dashboard', label: '数据看板', icon: '📊' },
  { to: '/help', name: 'help', label: '帮助', icon: '❓' }
]
</script>

<template>
  <div class="min-h-screen">
    <TopNav :items="navItems" :active="active" />

    <main class="mx-auto max-w-[1180px] px-4 lg:px-6 py-6 pb-24 lg:pb-10">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 移动端底部 Tab（中置「录入」突出） -->
    <nav class="lg:hidden fixed bottom-0 inset-x-0 z-50 bg-surface border-t border-line flex items-stretch" style="height: 60px">
      <router-link
        v-for="it in navItems" :key="it.name" :to="it.to"
        class="flex-1 flex flex-col items-center justify-center gap-0.5 text-cap text-body"
        :class="{ 'text-qblue font-semibold': active === it.name }"
      >
        <span class="text-[18px] leading-none">{{ it.icon }}</span>{{ it.label }}
      </router-link>
      <button class="flex-1 flex flex-col items-center justify-end pb-1 text-cap text-body" @click="store.openEntry()">
        <span
          class="-mt-6 mb-0.5 inline-flex items-center justify-center w-11 h-11 rounded-full bg-qblue text-white text-xl"
          style="box-shadow: 0 4px 12px rgba(59, 130, 246, .4)"
        >＋</span>录入
      </button>
    </nav>

    <!-- 全局录入弹窗 -->
    <EntryModal v-if="store.entryOpen" />

    <!-- toast -->
    <transition name="fade">
      <div
        v-if="store.toastMsg"
        class="fixed bottom-20 left-1/2 -translate-x-1/2 z-[80] bg-ink text-white text-body px-4 py-2.5 rounded-ctrl shadow-lg whitespace-nowrap"
      >{{ store.toastMsg }}</div>
    </transition>
  </div>
</template>
