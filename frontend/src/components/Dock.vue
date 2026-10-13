<script setup>
// The bar under Marshie: talk to her, tap the microphone, or type.
import { computed, ref } from 'vue'
import { brand } from '../brand'
import { lang, t } from '../i18n'
import { caps, send, state, toggleConversation, toggleListening, SPEAKING_MOODS } from '../composables/useMarshie'
import { canListen, listenLevel } from '../composables/useVoice'

const draft = ref('')

const listenable = computed(() => canListen())
const ring = computed(() => `${Math.round(listenLevel.value * 16)}px`)
const hint = computed(() => {
  if (caps.loaded && !listenable.value) {
    if (!caps.secure) return t('mic.needSecure')
    return lang() === 'en' ? t('mic.cantListen') : t('mic.cantListenLang')
  }
  if (state.conversation) {
    if (state.listening) return t('talk.hintListening')
    if (state.busy) return t('talk.hintThinking')
    if (SPEAKING_MOODS.includes(state.mood)) return t('talk.hintSpeaking', { name: brand.name })
    return t('talk.hintWait')
  }
  if (state.listening) return t('mic.listeningHint')
  return ''
})

function submit() {
  const text = draft.value.trim()
  if (!text || state.busy) return
  draft.value = ''
  send(text)
}
</script>

<template>
  <form class="dock" @submit.prevent="submit">
    <p v-if="hint" class="hint" aria-live="polite">{{ hint }}</p>
    <div class="row">
      <button
        v-if="listenable" type="button" class="btn talk" :class="state.conversation ? 'berry' : 'green'"
        :aria-pressed="state.conversation" :disabled="state.busy && !state.conversation" @click="toggleConversation"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <template v-if="!state.conversation"><rect x="9" y="3" width="6" height="12" rx="3" fill="currentColor" /><path d="M5 11a7 7 0 0014 0M12 18v3" /></template>
          <rect v-else x="6" y="6" width="12" height="12" rx="2.500" fill="currentColor" />
        </svg>
        <span class="label">{{ state.conversation ? t('talk.stop') : t('talk.start') }}</span>
      </button>

      <div class="inputwrap">
        <button
          type="button" class="mic" :class="{ live: state.listening, indicator: state.conversation }" :style="{ '--ring': ring }"
          :disabled="!listenable || state.busy || state.conversation" :aria-pressed="state.listening"
          :aria-label="state.listening ? t('mic.stop') : t('mic.ask', { name: brand.name })"
          @click="toggleListening"
        >
          <svg v-if="!state.listening || state.conversation" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="9" y="3" width="6" height="12" rx="3" fill="currentColor" /><path d="M5 11a7 7 0 0014 0M12 18v3" />
          </svg>
          <span v-else>{{ t('mic.stopShort') }}</span>
        </button>
        <input
          v-model="draft" class="field" type="text" maxlength="300" autocomplete="off" enterkeyhint="send"
          :placeholder="state.quiz?.current ? t('dock.placeholderQuiz') : t('dock.placeholder')"
          :aria-label="state.quiz?.current ? t('dock.answer') : t('dock.question')"
          :disabled="state.listening"
        />
      </div>

      <button class="btn pink send" type="submit" :disabled="!draft.trim() || state.busy || state.listening" :aria-label="t('dock.send')">
        <span class="label">{{ t('dock.send') }}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h15M13 6l6 6-6 6" /></svg>
      </button>
    </div>
  </form>
</template>

<style scoped>
.dock {
  width: min(56rem, 100%); margin: 0 auto; padding: .35rem .9rem calc(.8rem + env(safe-area-inset-bottom, 0px));
  display: flex; flex-direction: column; gap: .35rem;
}
.hint { text-align: center; min-height: 1.3rem; }
.row { display: flex; align-items: center; gap: .6rem; }

.talk { flex: none; gap: .5rem; padding: .5rem 1.2rem; font-size: 1.05rem; min-height: 3.4rem; }
.talk svg { width: 1.45rem; height: 1.45rem; }

.inputwrap { position: relative; flex: 1; min-width: 0; }
.inputwrap .field { font-size: 1.1rem; min-height: 3.4rem; padding-left: 4.1rem; border-radius: 999px; }
.mic {
  position: absolute; left: .4rem; top: 50%; translate: 0 -50%;
  width: 2.7rem; height: 2.7rem; border-radius: 50%; display: grid; place-items: center; cursor: pointer;
  background: var(--gold); color: var(--on-gold); border: 3px solid var(--ink); padding: 0;
  font-family: var(--display); font-weight: 800; font-size: .8rem; touch-action: manipulation;
  box-shadow: 0 0 0 var(--ring, 0px) rgba(229, 72, 77, .35);
  transition: background-color .12s, box-shadow .1s;
}
.mic svg { width: 1.45rem; height: 1.45rem; }
.mic.live { background: var(--berry); color: #fff; box-shadow: 0 0 0 calc(3px + var(--ring, 0px)) rgba(229, 72, 77, .35); }
.mic:disabled { opacity: .45; cursor: not-allowed; }
.mic.indicator:disabled { opacity: .65; cursor: default; }                /* in a conversation the mic only shows she is listening */
.mic.indicator.live:disabled { opacity: 1; }

.send { flex: none; min-height: 3.4rem; padding: .5rem 1.3rem; font-size: 1.05rem; }

@media (max-width: 560px) {
  .dock { padding-inline: .6rem; }
  .row { gap: .45rem; }
  .talk, .send { position: relative; width: 3.4rem; padding: 0; }
  .mic { display: none; }                                  /* on a phone the Talk button does the listening */
  .inputwrap .field { padding-left: 1rem; padding-right: .6rem; font-size: 1rem; }
  .talk .label, .send .label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .talk svg, .send svg { width: 1.6rem; height: 1.6rem; }
}
</style>
