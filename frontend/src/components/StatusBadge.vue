<script setup lang="ts">
defineProps<{ reviewed: boolean }>()
</script>

<template>
  <span
    v-if="reviewed"
    class="absolute top-4 right-4 text-cap font-semibold text-white bg-success px-2 py-0.5 rounded-tag"
  >✓ 已复习</span>
  <span
    v-else
    class="absolute top-4 right-4 text-cap font-semibold text-body bg-surface border border-dashed border-line px-2 py-0.5 rounded-tag"
  >○ 未复习</span>
</template>
