<script setup>
// "What we said": the whole conversation so far, for a teacher or a child who wants to look back.
import { nextTick, onMounted, ref } from 'vue'
import MessageItem from './MessageItem.vue'
import { t } from '../i18n'
import { ui } from '../ui'
import { state } from '../composables/useMarshie'

const list = ref(null)
const closeBtn = ref(null)

onMounted(async () => {
  await nextTick()
  if (list.value) list.value.scrollTop = list.value.scrollHeight
  closeBtn.value?.focus({ preventScroll: true })
})
const close = () => { ui.history = false }
</script>

<template>
  <div class="scrim" @pointerdown.self="close" @keydown.esc.stop="close">
    <aside class="sheet" role="dialog" aria-modal="true" :aria-label="t('menu.history')">
      <header>
        <h2>{{ t('menu.history') }}</h2>
        <button ref="closeBtn" type="button" class="btn small white" @click="close">{{ t('menu.close') }}</button>
      </header>
      <div ref="list" class="list" role="log">
        <p v-if="!state.messages.length" class="empty">{{ t('history.empty') }}</p>
        <MessageItem v-for="m in state.messages" :key="m.id" :m="m" variant="list" />
      </div>
    </aside>
  </div>
</template>

<style scoped>
.scrim { position: absolute; inset: 0; z-index: 9; background: rgba(2, 35, 45, .45); display: flex; justify-content: flex-end; }
.sheet {
  width: min(27rem, 100%); height: 100%; display: flex; flex-direction: column;
  background: var(--paper); border-left: 4px solid var(--ink); animation: slide .2s ease-out;
}
@keyframes slide { from { transform: translateX(2rem); opacity: 0 } }
header { display: flex; align-items: center; justify-content: space-between; gap: .8rem; padding: .8rem 1rem .6rem 1.2rem; border-bottom: 3px solid var(--ink); }
h2 { font-size: 1.4rem; }
.list { flex: 1; min-height: 0; overflow-y: auto; padding: 1rem 1.1rem 1.4rem; display: flex; flex-direction: column; gap: .9rem; }
.empty { color: var(--ink-soft); }
@media (max-width: 560px) { .sheet { border-left: 0; } }
</style>
