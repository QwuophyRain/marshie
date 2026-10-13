<script setup>
// One thing Marshie (or a child) said: the words, any pictures or recordings, and the buttons under an answer.
// Used twice: as the big subtitle card over Marshie ("card"), and in the "what we said" list ("list").
import { brand } from '../brand'
import { t } from '../i18n'
import { ui } from '../ui'
import { openTeach, rate, send, state, touch } from '../composables/useMarshie'
import { stopSpeaking } from '../composables/useVoice'

defineProps({
  m: { type: Object, required: true },
  variant: { type: String, default: 'card' },       // 'card' | 'list'
})

function onMediaPlay() {          // her own voice and a recording must not talk over each other
  stopSpeaking()
  touch()
}
function ask(question) {
  if (state.busy) return
  ui.menu = false
  ui.history = false
  send(question)
}
</script>

<template>
  <div class="item" :class="[`is-${variant}`, m.role]">
    <div v-if="variant === 'list'" class="bubble" :class="[m.role, m.kind, { right: m.correct === true, wrong: m.correct === false }]" :lang="m.lang">{{ m.text }}</div>
    <p v-else class="say" :class="{ long: m.text.length > 120 }" :lang="m.lang">{{ m.text }}</p>

    <div v-if="m.media?.length" class="media">
      <template v-for="f in m.media" :key="f.id">
        <button v-if="f.kind === 'image'" type="button" class="pic" :aria-label="t('msg.picture', { title: f.title })" @click="ui.zoom = f">
          <img :src="f.url" :alt="f.title" loading="lazy" />
        </button>
        <figure v-else class="clip">
          <figcaption>{{ f.title }}</figcaption>
          <video v-if="f.kind === 'video'" :src="f.url" controls playsinline preload="metadata" @play="onMediaPlay"></video>
          <audio v-else :src="f.url" controls preload="none" @play="onMediaPlay"></audio>
        </figure>
      </template>
    </div>
    <p v-if="m.origin?.startsWith('From ')" class="origin">{{ m.origin }}</p>

    <div v-if="m.role === 'bot' && (m.rateable || m.canTeach || m.feedback === 'bad')" class="actions">
      <template v-if="m.rateable && !m.feedback">
        <button class="btn small green" @click="rate(m, true)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12.500l5 5L20 6.500" /></svg>
          {{ t('msg.right') }}
        </button>
        <button class="btn small berry" @click="rate(m, false)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
          {{ t('msg.wrong') }}
        </button>
      </template>
      <p v-else-if="m.feedback === 'good'" class="rated">{{ t('msg.thanks') }}</p>
      <button v-if="m.canTeach || m.feedback === 'bad'" class="btn small pink" @click="openTeach(m.question)">
        {{ t('msg.teach', { name: brand.name }) }}
      </button>
    </div>

    <div v-if="m.alternatives?.length" class="actions">
      <button v-for="alt in m.alternatives" :key="alt.question" class="chip" @click="ask(alt.question)">
        {{ t('msg.didYouMean', { q: alt.question }) }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.item { display: flex; flex-direction: column; gap: .6rem; min-width: 0; }
.item.is-list { gap: .45rem; }
.item.is-list.user { align-items: flex-end; }
.item.is-list.bot { align-items: flex-start; }

/* the subtitle card shows her words large, hyphenating long German words instead of overflowing */
.say {
  font-size: clamp(1.1rem, .9rem + .85vw, 1.55rem); line-height: 1.38; font-weight: 700;
  white-space: pre-wrap; overflow-wrap: anywhere; hyphens: auto; -webkit-hyphens: auto;
}
.say.long { font-weight: 400; font-size: clamp(1.05rem, .85rem + .6vw, 1.3rem); line-height: 1.45; }

.bubble {
  max-width: 92%; padding: .65rem 1rem; font-size: 1rem; line-height: 1.45;
  border: 3px solid var(--ink); white-space: pre-wrap; overflow-wrap: anywhere; hyphens: auto;
}
.bubble.bot { background: var(--pink-wash); border-radius: 22px 22px 22px 6px; }
.bubble.user { background: var(--sky); border-radius: 22px 22px 6px 22px; }
.bubble.error { background: #fff; border-style: dashed; border-color: var(--berry); }
.bubble.quiz, .bubble.thanks, .bubble.quiz-end { background: var(--note); }
.bubble.quiz-result.right { background: var(--good-bg); }
.bubble.quiz-result.wrong { background: #ffd9d9; }

.media { display: flex; flex-wrap: wrap; gap: .6rem; }
.pic { all: unset; cursor: zoom-in; display: block; border: 3px solid var(--ink); border-radius: 18px; overflow: hidden; background: #fff; box-shadow: 0 4px 0 var(--ink); }
.pic:focus-visible { outline: 4px solid var(--ink); outline-offset: 3px; }
.pic img { display: block; max-width: min(100%, 20rem); max-height: 11rem; object-fit: contain; }
.clip { margin: 0; padding: .5rem .7rem; max-width: 100%; border: 3px solid var(--ink); border-radius: 18px; background: #fff; display: flex; flex-direction: column; gap: .35rem; }
.clip figcaption { font-weight: 700; font-size: .95rem; }
.clip audio { width: min(100%, 18rem); }
.clip video { width: min(100%, 22rem); max-height: 12rem; border-radius: 12px; background: #000; }
.origin { font-size: .85rem; color: var(--ink-soft); }

.actions { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.rated { color: var(--ink-soft); font-weight: 700; }
.chip {
  padding: .45rem .95rem; background: #fff; border: 3px solid var(--ink); border-radius: 999px;
  font-weight: 700; font-size: .95rem; cursor: pointer; text-align: left; touch-action: manipulation;
  transition: background-color .12s, transform .08s;
}
.chip:hover { background: var(--pink-wash); }
.chip:active { transform: scale(.97); }
@media (max-width: 560px) { .actions .btn.small { padding: .3rem .75rem; font-size: .85rem; } }
</style>
