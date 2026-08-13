<script setup lang="ts">
defineProps<{
  items: { to: string; name: string; label: string; icon: string }[]
  active: string
}>()
</script>

<template>
  <header class="glass sticky top-0 z-40 h-14 flex items-center gap-4 px-4 lg:px-6 border-b border-line">
    <router-link to="/" class="flex items-center gap-2 shrink-0">
      <span class="text-xl font-bold tracking-wide text-qblue">Recall<span class="text-ink">·AI 错题本</span></span>
    </router-link>
    <nav class="hidden lg:flex gap-2 ml-auto">
      <router-link
        v-for="it in items" :key="it.name" :to="it.to"
        class="px-3.5 py-1.5 rounded-ctrl text-body hover:bg-surface transition"
        :class="{ 'text-qblue font-semibold bg-cblue/10': active === it.name }"
      >{{ it.icon }} {{ it.label }}</router-link>
    </nav>
  </header>
</template>
