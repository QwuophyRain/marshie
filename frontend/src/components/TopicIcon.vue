<script setup>
defineProps({ id: { type: String, required: true } })
</script>

<template>
  <svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">
    <!-- school: a building with a flag -->
    <g v-if="id === 'school'"><path d="M7 41V21l17-10 17 10v20z" /><path d="M20 41V29h8v12" /><path d="M24 11V4l7 2.500-7 2.500" /></g>
    <!-- maths: plus and equals -->
    <g v-else-if="id === 'maths'"><path d="M13 16h14M20 9v14" /><path d="M13 35h22M13 41h22" /><path d="M32 12l8 8M40 12l-8 8" /></g>
    <!-- english: open book with an A -->
    <g v-else-if="id === 'english'"><path d="M6 11c7-2 13-1 18 3 5-4 11-5 18-3v27c-7-2-13-1-18 3-5-4-11-5-18-3z" /><path d="M24 14v27" /><path d="M13 28l4-9 4 9M14.6 25h4.8" /></g>
    <!-- science: flask -->
    <g v-else-if="id === 'science'"><path d="M19 6h10M21 6v13L9 38c-1.5 3 .3 5 3 5h24c2.700 0 4.500-2 3-5L27 19V6" /><path d="M14 31h20" /></g>
    <!-- ghana: black star -->
    <g v-else-if="id === 'ghana'"><path d="M24 5l5.600 12.200 13.400 1.500-10 9 2.800 13.200L24 34l-11.800 6.900 2.800-13.200-10-9 13.400-1.500z" fill="currentColor" /></g>
    <!-- arts: palette -->
    <g v-else-if="id === 'arts'"><path d="M24 6C13 6 5 14 5 24s8 18 18 18c3 0 4-2 3-4-1-2.500 0-5 3-5h5c5 0 8-3 8-8C42 14 34 6 24 6z" /><circle cx="15" cy="22" r="2.200" fill="currentColor" /><circle cx="22" cy="14" r="2.200" fill="currentColor" /><circle cx="32" cy="16" r="2.200" fill="currentColor" /></g>
    <!-- fun: a smiling face -->
    <g v-else-if="id === 'fun'"><circle cx="24" cy="24" r="18" /><circle cx="17.500" cy="20" r="2.200" fill="currentColor" /><circle cx="30.500" cy="20" r="2.200" fill="currentColor" /><path d="M15 28c2 6 16 6 18 0" /></g>
    <!-- tech: chip -->
    <g v-else><rect x="12" y="12" width="24" height="24" rx="4" /><rect x="19" y="19" width="10" height="10" rx="1.500" /><path d="M18 5v7M24 5v7M30 5v7M18 36v7M24 36v7M30 36v7M5 18h7M5 24h7M5 30h7M36 18h7M36 24h7M36 30h7" /></g>
  </svg>
</template>
