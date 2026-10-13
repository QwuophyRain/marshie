<script setup>
// The subtitle card over the bottom of the screen: what Marshie just said, in large writing, with the question above it.
import { computed, nextTick, ref, watch } from 'vue'
import MessageItem from './MessageItem.vue'
import { brand } from '../brand'
import { t } from '../i18n'
import { state } from '../composables/useMarshie'
import { liveText } from '../composables/useVoice'

const scroller = ref(null)

const last = computed(() => state.messages[state.messages.length - 1] || null)
// the child's words that led to what is on the card
const asked = computed(() => {
  const i = state.messages.length - 1
  if (state.listening && liveText.value) return ''
  if (state.busy) return lastUser(i)
  return last.value?.role === 'bot' ? lastUser(i - 1, true) : ''
})
function lastUser(from, directlyBefore = false) {
  const m = state.messages[from]
  if (m?.role === 'user') return m.text
  if (directlyBefore) return ''
  for (let i = from; i >= 0; i--) if (state.messages[i].role === 'user') return state.messages[i].text
  return ''
}

const hearing = computed(() => state.listening && !!liveText.value)
const thinking = computed(() => state.busy)
const shown = computed(() => (hearing.value || thinking.value ? null : last.value))
const visible = computed(() => hearing.value || thinking.value || !!last.value)
const hasMedia = computed(() => !!shown.value?.media?.length)
const tone = computed(() => {
  const m = shown.value
  if (hearing.value) return 'hearing'
  if (!m) return ''
  if (m.kind === 'error') return 'error'
  if (m.kind === 'quiz' || m.kind === 'quiz-end' || m.kind === 'thanks') return 'note'
  if (m.kind === 'quiz-result') return m.correct ? 'right' : 'wrong'
  return ''
})

watch(
  () => [state.messages.length, state.busy, liveText.value],
  async () => {
    await nextTick()
    if (scroller.value) scroller.value.scrollTop = 0
  },
)
</script>

<template>
  <section v-if="visible" class="card-wrap" :aria-label="t('msg.chatAria', { name: brand.name })">
    <p v-if="asked" class="asked" :title="asked">{{ asked }}</p>
    <Transition name="pop" mode="out-in">
      <div :key="hearing ? 'hearing' : thinking ? 'thinking' : shown?.id" class="subtitle" :class="[tone, { media: hasMedia }]">
        <div ref="scroller" class="scroll" aria-live="polite" aria-atomic="true">
          <p v-if="hearing" class="say hearing">{{ liveText }}…</p>
          <div v-else-if="thinking" class="dots" role="status" :aria-label="t('msg.thinkingAria', { name: brand.name })"><i></i><i></i><i></i></div>
          <MessageItem v-else-if="shown" :m="shown" variant="card" />
        </div>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.card-wrap {
  position: absolute; z-index: 3; left: 50%; transform: translateX(-50%);
  bottom: 1rem;
  bottom: clamp(.5rem, 2.2cqh, 1.4rem);
  width: min(46rem, calc(100% - 1.4rem));
  display: flex; flex-direction: column; align-items: flex-start;
  pointer-events: none;
}
.card-wrap > * { pointer-events: auto; }

/* the question, like a tab on the top edge of the card */
.asked {
  position: relative; z-index: 1; margin: 0 0 -3px 1.2rem; max-width: calc(100% - 2.4rem);
  padding: .2rem .9rem .3rem; font-size: .92rem; font-weight: 700; line-height: 1.25;
  background: var(--sky); color: var(--ink); border: 3px solid var(--ink); border-bottom: 0; border-radius: 14px 14px 0 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.subtitle {
  width: 100%; background: #fff; color: var(--ink);
  border: 4px solid var(--ink); border-radius: 26px; box-shadow: 0 6px 0 var(--ink);
}
.subtitle.note { background: var(--note); }
.subtitle.right { background: var(--good-bg); }
.subtitle.wrong { background: #ffd9d9; }
.subtitle.error { border-style: dashed; border-color: var(--berry); }
.subtitle.hearing { border-style: dashed; }

.scroll {
  padding: .8rem 1.25rem .9rem; overflow-y: auto; overscroll-behavior: contain;
  max-height: 24vh; max-height: 24cqh;
}
.subtitle.media .scroll { max-height: 46vh; max-height: 46cqh; }
.say.hearing { font-size: clamp(1.1rem, .9rem + .85vw, 1.55rem); line-height: 1.38; font-weight: 700; opacity: .75; }

.dots { display: inline-flex; gap: .45rem; padding: .35rem .2rem; }
.dots i { width: .8rem; height: .8rem; border-radius: 50%; background: var(--ink); animation: hop 1s ease-in-out infinite; }
.dots i:nth-child(2) { animation-delay: .15s; }
.dots i:nth-child(3) { animation-delay: .3s; }
@keyframes hop { 0%, 60%, 100% { transform: translateY(0); opacity: .45 } 30% { transform: translateY(-7px); opacity: 1 } }

/* a new card pops up from the bottom: motion that answers what the child just did */
.pop-enter-active { transition: transform .22s cubic-bezier(.3, 1.4, .5, 1), opacity .15s; }
.pop-leave-active { transition: opacity .08s; }
.pop-enter-from { transform: translateY(14px) scale(.97); opacity: 0; }
.pop-leave-to { opacity: 0; }

@media (min-width: 901px) and (orientation: landscape) and (max-height: 780px) {
  .scroll { max-height: 22vh; max-height: 22cqh; }
}
@media (max-width: 560px) {
  .scroll { padding: .65rem .95rem .75rem; }
  .asked { margin-left: .8rem; font-size: .85rem; }
}
</style>
