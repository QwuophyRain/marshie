<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import TopicIcon from './TopicIcon.vue'
import { TOPICS, STARTERS } from '../topics'
import {
  state, caps, send, toggleListening, toggleConversation, rate, openTeach, stopQuiz, resetConversation, touch, SPEAKING_MOODS,
} from '../composables/useMarshie'
import { canListen, listenLevel, liveText, stopSpeaking } from '../composables/useVoice'

const draft = ref('')
const log = ref(null)
const openTopic = ref('')
const showIdeas = ref(false)
const zoom = ref(null)            // a picture opened full size

const ideasVisible = computed(() => !state.quiz && !state.conversation && (state.messages.length <= 1 || showIdeas.value))
const topic = computed(() => TOPICS.find((t) => t.id === openTopic.value))
const listenable = computed(() => canListen())
const micHint = computed(() => {
  if (!caps.loaded || listenable.value) return ''
  return caps.secure
    ? 'This browser can’t listen yet, so please type your question.'
    : 'The microphone needs the address http://localhost:8000 (or HTTPS). You can type for now.'
})
const ring = computed(() => `${Math.round(listenLevel.value * 16)}px`)
const talkHint = computed(() => {
  if (!state.conversation) return 'Press the button and we can chat out loud. No tapping needed.'
  if (state.listening) return 'I’m listening. Just talk to me.'
  if (state.busy) return 'Thinking…'
  if (SPEAKING_MOODS.includes(state.mood)) return 'Tap Marshie to stop her and speak.'
  return 'One moment…'
})

function submit() {
  const text = draft.value.trim()
  if (!text || state.busy) return
  draft.value = ''
  showIdeas.value = false
  send(text)
}

function ask(text) {
  if (state.busy) return
  showIdeas.value = false
  openTopic.value = ''
  send(text)
}

function onMediaPlay() {          // her own voice and a recording must not talk over each other
  stopSpeaking()
  touch()
}

function toggleIdeas() {
  touch()
  showIdeas.value = !showIdeas.value
  if (!showIdeas.value) openTopic.value = ''
}

watch(
  () => [state.messages.length, state.busy, state.quiz?.current?.question],
  async () => {
    await nextTick()
    const el = log.value
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  },
)
</script>

<template>
  <section class="panel" aria-label="Chat with Marshie">
    <div ref="log" class="log" role="log" aria-live="polite">
      <template v-for="m in state.messages" :key="m.id">
        <div class="row" :class="m.role">
          <div class="bubble" :class="[m.role, m.kind, { right: m.correct === true, wrong: m.correct === false }]">
            {{ m.text }}
          </div>
        </div>

        <div v-if="m.media?.length" class="row bot media">
          <template v-for="f in m.media" :key="f.id">
            <button v-if="f.kind === 'image'" type="button" class="pic" :aria-label="`Open the picture: ${f.title}`" @click="zoom = f">
              <img :src="f.url" :alt="f.title" loading="lazy" />
            </button>
            <figure v-else class="clip">
              <figcaption>{{ f.title }}</figcaption>
              <video v-if="f.kind === 'video'" :src="f.url" controls playsinline preload="metadata" @play="onMediaPlay"></video>
              <audio v-else :src="f.url" controls preload="none" @play="onMediaPlay"></audio>
            </figure>
          </template>
        </div>
        <p v-if="m.origin?.startsWith('From ')" class="row bot origin">{{ m.origin }}</p>

        <div v-if="m.role === 'bot' && (m.rateable || m.canTeach || m.feedback === 'bad')" class="row bot actions">
          <template v-if="m.rateable && !m.feedback">
            <button class="btn small green" @click="rate(m, true)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12.500l5 5L20 6.500" /></svg>
              That’s right
            </button>
            <button class="btn small berry" @click="rate(m, false)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
              That’s wrong
            </button>
          </template>
          <p v-else-if="m.feedback === 'good'" class="rated">Thank you for telling me!</p>
          <button v-if="m.canTeach || m.feedback === 'bad'" class="btn small pink" @click="openTeach(m.question)">
            Teach Marshie the answer
          </button>
        </div>

        <div v-if="m.alternatives?.length" class="row bot actions">
          <button v-for="alt in m.alternatives" :key="alt.question" class="chip" @click="ask(alt.question)">
            Did you mean “{{ alt.question }}”?
          </button>
        </div>
      </template>

      <div v-if="state.listening && liveText" class="row user" aria-hidden="true">
        <div class="bubble user live">{{ liveText }}…</div>
      </div>
      <div v-else-if="state.listening && state.conversation" class="row user" aria-hidden="true">
        <div class="bubble user dots live"><i></i><i></i><i></i></div>
      </div>

      <div v-if="state.busy" class="row bot" aria-label="Marshie is thinking">
        <div class="bubble bot dots" aria-hidden="true"><i></i><i></i><i></i></div>
      </div>

      <div v-if="ideasVisible" class="ideas">
        <div class="topics">
          <button
            v-for="t in TOPICS" :key="t.id" class="topic" :class="{ on: openTopic === t.id }"
            :style="{ '--tc': t.color, '--tf': t.fg || 'var(--ink)' }" :aria-pressed="openTopic === t.id"
            @click="openTopic = openTopic === t.id ? '' : t.id"
          >
            <TopicIcon :id="t.id" />
            {{ t.label }}
          </button>
        </div>
        <div class="chips">
          <template v-if="topic">
            <button v-for="q in topic.questions" :key="q" class="chip" @click="ask(q)">{{ q }}</button>
          </template>
          <template v-else>
            <button v-for="q in STARTERS" :key="q" class="chip" @click="ask(q)">{{ q }}</button>
          </template>
        </div>
      </div>
    </div>

    <div v-if="zoom" class="lightbox" role="dialog" aria-modal="true" :aria-label="zoom.title" @click="zoom = null" @keydown.esc="zoom = null">
      <img :src="zoom.url" :alt="zoom.title" />
      <p>{{ zoom.title }}</p>
      <button class="btn small white" type="button" autofocus @click.stop="zoom = null">Close</button>
    </div>

    <div v-if="state.quiz" class="quizbar">
      <p>
        Quiz time. You have {{ state.quiz.score }} right out of {{ state.quiz.total }}.
      </p>
      <button class="btn small white" @click="stopQuiz">Stop quiz</button>
    </div>

    <div v-if="listenable" class="talkbar">
      <button
        type="button" class="btn talk" :class="state.conversation ? 'berry' : 'green'" :aria-pressed="state.conversation"
        :disabled="state.busy && !state.conversation" @click="toggleConversation"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect v-if="!state.conversation" x="9" y="3" width="6" height="12" rx="3" fill="currentColor" /><path v-if="!state.conversation" d="M5 11a7 7 0 0014 0M12 18v3" />
          <rect v-else x="6" y="6" width="12" height="12" rx="2.500" fill="currentColor" />
        </svg>
        {{ state.conversation ? 'Stop talking' : 'Talk with me' }}
      </button>
      <p class="hint" aria-live="polite">{{ talkHint }}</p>
    </div>

    <form class="composer" @submit.prevent="submit">
      <button
        type="button" class="mic" :class="{ live: state.listening, indicator: state.conversation }" :style="{ '--ring': ring }"
        :disabled="!listenable || state.busy || state.conversation" :aria-pressed="state.listening"
        :aria-label="state.listening ? 'Stop listening' : 'Tap and ask Marshie a question'"
        @click="toggleListening"
      >
        <svg v-if="!state.listening || state.conversation" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="9" y="3" width="6" height="12" rx="3" fill="currentColor" /><path d="M5 11a7 7 0 0014 0M12 18v3" />
        </svg>
        <span v-else>Stop</span>
      </button>
      <input
        v-model="draft" class="field" type="text" maxlength="300" autocomplete="off" enterkeyhint="send"
        :placeholder="state.quiz?.current ? 'Type your answer' : 'Type your question here'"
        :aria-label="state.quiz?.current ? 'Your answer' : 'Your question'"
        :disabled="state.listening"
      />
      <button class="btn pink" type="submit" :disabled="!draft.trim() || state.busy || state.listening">Send</button>
    </form>

    <div class="foot">
      <p v-if="micHint" class="hint">{{ micHint }}</p>
      <p v-else-if="state.listening && !state.conversation" class="hint">I’m listening. Say your question, then wait a moment.</p>
      <span class="spacer"></span>
      <button v-if="!state.quiz && state.messages.length > 1" class="btn small ghost" type="button" @click="toggleIdeas">
        {{ showIdeas ? 'Hide ideas' : 'Show ideas' }}
      </button>
      <button class="btn small ghost" type="button" @click="resetConversation">Start fresh</button>
    </div>
  </section>
</template>

<style scoped>
.panel {
  position: relative;
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  background: #fff; border: 4px solid var(--ink); border-radius: 32px; box-shadow: 0 8px 0 var(--ink);
  overflow: hidden;
}

.log { flex: 1; min-height: 0; overflow-y: auto; padding: 1.2rem 1.3rem .6rem; display: flex; flex-direction: column; gap: .7rem; scroll-behavior: smooth; }

.row { display: flex; }
.row.user { justify-content: flex-end; }
.row.actions { flex-wrap: wrap; gap: .55rem; align-items: center; margin-top: -.15rem; }
.bubble {
  max-width: 88%; padding: .7rem 1.05rem; font-size: 1.12rem; line-height: 1.45;
  border: 3px solid var(--ink); white-space: pre-wrap; overflow-wrap: anywhere;
}
.bubble.bot { background: var(--pink-wash); border-radius: 24px 24px 24px 6px; }
.bubble.user { background: var(--sky); border-radius: 24px 24px 6px 24px; }
.bubble.error { background: #fff; border-style: dashed; border-color: var(--berry); }
.bubble.quiz { background: var(--note); }
.bubble.quiz-result.right { background: var(--good-bg); }
.bubble.quiz-result.wrong { background: #ffd9d9; }
.bubble.thanks, .bubble.quiz-end { background: var(--note); }

.media { margin-top: -.2rem; }
.pic { all: unset; cursor: zoom-in; display: block; border: 3px solid var(--ink); border-radius: 20px; overflow: hidden; background: #fff; box-shadow: 0 4px 0 var(--ink); }
.pic:focus-visible { outline: 4px solid var(--ink); outline-offset: 3px; }
.pic img { display: block; max-width: min(100%, 22rem); max-height: 15rem; object-fit: contain; }
.clip { margin: 0; padding: .6rem .8rem; max-width: 100%; border: 3px solid var(--ink); border-radius: 20px; background: #fff; display: flex; flex-direction: column; gap: .4rem; }
.clip figcaption { font-weight: 700; }
.clip audio { width: min(100%, 20rem); }
.clip video { width: min(100%, 24rem); max-height: 16rem; border-radius: 12px; background: #000; }
.origin { font-size: .85rem; color: var(--ink-soft); margin-top: -.3rem; padding-left: .4rem; }
.lightbox { position: absolute; inset: 0; z-index: 5; background: rgba(2, 35, 45, .86); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .8rem; padding: 1rem; cursor: zoom-out; }
.lightbox img { max-width: 100%; max-height: calc(100% - 7rem); object-fit: contain; background: #fff; border-radius: 16px; border: 4px solid #fff; }
.lightbox p { color: #fff; font-weight: 700; font-size: 1.15rem; text-align: center; }

.dots { display: inline-flex; gap: .4rem; padding: .95rem 1.2rem; }
.dots i { width: .7rem; height: .7rem; border-radius: 50%; background: var(--ink); animation: hop 1s ease-in-out infinite; }
.dots i:nth-child(2) { animation-delay: .15s; }
.dots i:nth-child(3) { animation-delay: .3s; }
@keyframes hop { 0%, 60%, 100% { transform: translateY(0); opacity: .45 } 30% { transform: translateY(-7px); opacity: 1 } }

.rated { color: var(--ink-soft); font-weight: 700; padding-left: .3rem; }

.chip {
  padding: .5rem 1rem; background: #fff; border: 3px solid var(--ink); border-radius: 999px;
  font-weight: 700; font-size: 1rem; cursor: pointer; text-align: left; touch-action: manipulation;
  transition: background-color .12s, transform .08s;
}
.chip:hover { background: var(--pink-wash); }
.chip:active { transform: scale(.97); }

.ideas { display: flex; flex-direction: column; gap: .8rem; margin-top: .4rem; }
.topics { display: grid; grid-template-columns: repeat(auto-fit, minmax(8.6rem, 1fr)); gap: .6rem; }
.topic {
  display: flex; align-items: center; gap: .55rem; padding: .55rem .8rem;
  font-family: var(--display); font-weight: 700; font-size: 1.05rem;
  background: var(--tc); color: var(--tf, var(--ink)); border: 3px solid var(--ink); border-radius: 18px; box-shadow: 0 4px 0 var(--ink);
  cursor: pointer; touch-action: manipulation; transition: transform .08s, box-shadow .08s;
}
.topic svg { width: 1.9rem; height: 1.9rem; flex: none; }
.topic:active { transform: translateY(4px); box-shadow: none; }
.topic.on { transform: translateY(4px); box-shadow: none; outline: 3px solid var(--ink); outline-offset: 3px; }
.chips { display: flex; flex-wrap: wrap; gap: .55rem; }

.quizbar {
  display: flex; align-items: center; justify-content: space-between; gap: .8rem; flex-wrap: wrap;
  padding: .55rem 1.3rem; background: var(--note); border-top: 3px solid var(--ink); font-weight: 700;
}

.talkbar { display: flex; align-items: center; gap: .9rem; flex-wrap: wrap; padding: .65rem 1.1rem .1rem; border-top: 3px solid var(--ink); }
.talkbar .hint { flex: 1 1 11rem; font-size: .95rem; }
.talk { gap: .5rem; padding: .55rem 1.3rem; font-size: 1.1rem; }
.talk svg { width: 1.5rem; height: 1.5rem; flex: none; }
.talkbar + .composer { border-top: 0; padding-top: .55rem; }
.bubble.live { opacity: .8; border-style: dashed; }
.bubble.live.dots { padding: .8rem 1.1rem; }
.composer { display: flex; align-items: center; gap: .7rem; padding: .8rem 1.1rem .5rem; border-top: 3px solid var(--ink); }
.composer .field { flex: 1; min-width: 0; font-size: 1.1rem; }
.mic {
  flex: none; width: 4.4rem; height: 4.4rem; border-radius: 50%;
  display: grid; place-items: center; cursor: pointer;
  background: var(--gold); border: 3px solid var(--ink); box-shadow: 0 5px 0 var(--ink), 0 0 0 var(--ring, 0px) rgba(229, 72, 77, .35);
  font-family: var(--display); font-weight: 800; font-size: 1.05rem; touch-action: manipulation;
  transition: transform .08s, box-shadow .1s;
}
.mic svg { width: 2.2rem; height: 2.2rem; }
.mic:active:not(:disabled) { transform: translateY(5px); box-shadow: 0 0 0 var(--ink), 0 0 0 var(--ring, 0px) rgba(229, 72, 77, .35); }
.mic.live { background: var(--berry); color: #fff; box-shadow: 0 5px 0 var(--ink), 0 0 0 calc(4px + var(--ring, 0px)) rgba(229, 72, 77, .35); }
.mic:disabled { opacity: .45; cursor: not-allowed; box-shadow: 0 2px 0 var(--ink); }
.mic.indicator:disabled { opacity: .6; cursor: default; }                 /* during a conversation the mic only shows she is listening */
.mic.indicator.live:disabled { opacity: 1; box-shadow: 0 5px 0 var(--ink), 0 0 0 calc(4px + var(--ring, 0px)) rgba(229, 72, 77, .35); }

.foot { display: flex; align-items: center; gap: .5rem; padding: .1rem 1.1rem .7rem; flex-wrap: wrap; min-height: 2.2rem; }
.foot .hint { flex: 1 1 14rem; }
.spacer { flex: 1; }

@media (max-width: 560px) {
  .log { padding: .9rem .8rem .4rem; }
  .bubble { max-width: 94%; font-size: 1.05rem; }
  .composer { padding: .7rem .7rem .4rem; gap: .5rem; }
  .mic { width: 3.8rem; height: 3.8rem; }
}
</style>
