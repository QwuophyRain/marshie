<script setup>
// The small menu box: language, boy or girl voice, ideas to ask, how to use Marshie, and a few buttons.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import TopicIcon from './TopicIcon.vue'
import { settings } from '../settings'
import { LANGUAGE_LIST, t } from '../i18n'
import { topics } from '../topics'
import { ui } from '../ui'
import { resetConversation, send, setGender, setLanguage, state } from '../composables/useMarshie'

const emit = defineEmits(['teachers'])

const box = ref(null)
const topicId = ref('')
const allTopics = computed(() => topics())
const openTopic = computed(() => allTopics.value.find((x) => x.id === topicId.value))
const girl = computed(() => settings.voiceGender !== 'male')

const canFullscreen = typeof document !== 'undefined' && !!document.documentElement.requestFullscreen
const fullscreen = ref(false)
const onFullscreen = () => { fullscreen.value = !!document.fullscreenElement }
async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
    else await document.documentElement.requestFullscreen()
  } catch { /* the browser said no; nothing to do */ }
}

const close = () => { ui.menu = false }
function ask(question) {
  if (state.busy) return
  close()
  send(question)
}
async function pickLanguage(code) {
  close()
  await setLanguage(code)
}
function pickVoice(gender) {
  setGender(gender)
}
function fresh() {
  close()
  resetConversation()
}
function openHistory() {
  close()
  ui.history = true
}
function teachers() {
  close()
  emit('teachers')
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreen)
  onFullscreen()
  nextTick(() => box.value?.querySelector('.pill.on, button')?.focus({ preventScroll: true }))
})
onBeforeUnmount(() => document.removeEventListener('fullscreenchange', onFullscreen))
</script>

<template>
  <div ref="box" class="menu" role="dialog" :aria-label="t('menu.open')" @keydown.esc.stop="close">
    <div class="head">
      <button v-if="openTopic" type="button" class="back" @click="topicId = ''">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
        {{ t('menu.back') }}
      </button>
      <strong v-else class="title">{{ t('menu.open') }}</strong>
      <strong v-if="openTopic" class="title">{{ openTopic.label }}</strong>
      <button type="button" class="x" :aria-label="t('menu.close')" @click="close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
      </button>
    </div>

    <div class="body">
      <ul v-if="openTopic" class="qs">
        <li v-for="q in openTopic.questions" :key="q"><button type="button" class="q" @click="ask(q)">{{ q }}</button></li>
      </ul>

      <template v-else>
        <section>
          <h3>{{ t('menu.language') }}</h3>
          <div class="langs" role="group" :aria-label="t('menu.language')">
            <button
              v-for="l in LANGUAGE_LIST" :key="l.code" type="button" class="pill" :class="{ on: settings.language === l.code }"
              :aria-pressed="settings.language === l.code" :lang="l.code" @click="pickLanguage(l.code)"
            >{{ l.native }}</button>
          </div>
        </section>

        <section>
          <h3>{{ t('menu.voice') }}</h3>
          <div class="voices" role="group" :aria-label="t('menu.voice')">
            <button type="button" class="pill voice" :class="{ on: girl }" :aria-pressed="girl" @click="pickVoice('female')">
              <svg viewBox="0 0 40 28" aria-hidden="true">
                <path d="M19 14C13 4 4 6 6 15c1.500 7 10 3 13-1zM21 14c6-10 15-8 13 1-1.500 7-10 3-13-1z" style="fill: var(--bow); stroke: var(--bow-dark)" stroke-width="2.200" stroke-linejoin="round" />
                <circle cx="20" cy="14" r="4.500" style="fill: var(--bow); stroke: var(--bow-dark)" stroke-width="2.200" />
              </svg>
              <span>{{ t('voice.girl') }}<small>{{ t('voice.girlNote') }}</small></span>
            </button>
            <button type="button" class="pill voice" :class="{ on: !girl }" :aria-pressed="!girl" @click="pickVoice('male')">
              <svg viewBox="0 0 40 28" aria-hidden="true">
                <path d="M18 14L4 6c-2 5-2 11 0 16z" style="fill: var(--c1); stroke: var(--ink)" stroke-width="2.200" stroke-linejoin="round" />
                <path d="M22 14l14-8c2 5 2 11 0 16z" style="fill: var(--c1); stroke: var(--ink)" stroke-width="2.200" stroke-linejoin="round" />
                <rect x="16" y="9" width="8" height="10" rx="3" style="fill: var(--c2); stroke: var(--ink)" stroke-width="2.200" />
              </svg>
              <span>{{ t('voice.boy') }}<small>{{ t('voice.boyNote') }}</small></span>
            </button>
          </div>
        </section>

        <section v-if="state.started">
          <h3>{{ t('menu.ask') }}</h3>
          <div class="tiles">
            <button
              v-for="x in allTopics" :key="x.id" type="button" class="tile"
              :style="{ '--tc': x.color, '--tf': x.fg || 'var(--ink)' }" @click="topicId = x.id"
            >
              <TopicIcon :id="x.id" />
              <span>{{ x.label }}</span>
            </button>
          </div>
        </section>

        <details class="how">
          <summary>{{ t('menu.how') }}</summary>
          <ul><li v-for="line in t('menu.howList')" :key="line">{{ line }}</li></ul>
        </details>

        <div class="actions">
          <button v-if="canFullscreen" type="button" class="act" @click="toggleFullscreen">
            {{ fullscreen ? t('menu.fullscreenExit') : t('menu.fullscreen') }}
          </button>
          <button v-if="state.messages.length" type="button" class="act" @click="openHistory">{{ t('menu.history') }}</button>
          <button v-if="state.started" type="button" class="act" @click="fresh">{{ t('menu.fresh') }}</button>
          <button type="button" class="act teachers" @click="teachers">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.600" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 018 0v3" />
            </svg>
            {{ t('menu.teachers') }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.menu {
  position: absolute; z-index: 8; top: 4.3rem; right: .9rem;
  width: min(20rem, calc(100% - 1.8rem)); max-height: calc(100% - 5.2rem);
  display: flex; flex-direction: column;
  background: var(--paper); color: var(--ink); font-size: .85rem; line-height: 1.35;
  border: 3px solid var(--ink); border-radius: 22px; box-shadow: 0 6px 0 var(--ink);
  transform-origin: top right; animation: open .16s cubic-bezier(.3, 1.3, .5, 1);
}
@keyframes open { from { transform: scale(.94); opacity: 0 } }

.head { display: flex; align-items: center; gap: .5rem; padding: .5rem .5rem .4rem 1rem; border-bottom: 3px solid var(--ink); }
.title { font-family: var(--display); font-size: 1.1rem; flex: 1; min-width: 0; }
.back { all: unset; cursor: pointer; display: inline-flex; align-items: center; gap: .15rem; font-weight: 700; padding: .25rem .5rem .25rem .15rem; border-radius: 999px; }
.back:hover { background: var(--sky); }
.back svg { width: 1.1rem; height: 1.1rem; }
.head .back + .title { text-align: center; }
.x { all: unset; cursor: pointer; flex: none; width: 2.1rem; height: 2.1rem; border-radius: 50%; display: grid; place-items: center; }
.x:hover { background: var(--sky); }
.x svg { width: 1.1rem; height: 1.1rem; }
.back:focus-visible, .x:focus-visible { outline: 3px solid var(--ink); outline-offset: 1px; box-shadow: none; }

.body { overflow-y: auto; overscroll-behavior: contain; padding: .6rem .8rem .8rem; display: flex; flex-direction: column; gap: .75rem; }
h3 { font-family: var(--text); font-size: .85rem; font-weight: 700; color: var(--ink-soft); margin-bottom: .3rem; }

.pill {
  min-height: 2.2rem; padding: .2rem .5rem; background: #fff; color: var(--ink); cursor: pointer;
  border: 3px solid var(--ink); border-radius: 999px; font-weight: 700; font-size: .85rem; touch-action: manipulation;
  transition: background-color .12s, transform .08s;
}
.pill:active { transform: scale(.96); }
.pill.on { background: var(--gold); color: var(--on-gold); box-shadow: 0 3px 0 var(--ink); }
.langs { display: grid; grid-template-columns: repeat(4, 1fr); gap: .35rem; }
.langs .pill { padding-inline: .15rem; font-size: .8rem; }

.voices { display: grid; grid-template-columns: 1fr 1fr; gap: .4rem; }
.voice { display: flex; align-items: center; gap: .45rem; border-radius: 18px; padding: .3rem .6rem .3rem .45rem; text-align: left; }
.voice svg { width: 2.2rem; height: 1.6rem; flex: none; }
.voice span { display: flex; flex-direction: column; line-height: 1.1; }
.voice small { font-weight: 400; font-size: .68rem; color: var(--ink-soft); margin-top: .1rem; }
.voice.on small { color: var(--ink); }

.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: .4rem; }
.tile {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .15rem; min-height: 4rem; padding: .3rem .15rem;
  font-family: var(--display); font-weight: 700; font-size: .72rem; line-height: 1.05; text-align: center; overflow-wrap: anywhere;
  background: var(--tc); color: var(--tf); border: 3px solid var(--ink); border-radius: 16px; box-shadow: 0 3px 0 var(--ink);
  cursor: pointer; touch-action: manipulation; transition: transform .08s, box-shadow .08s;
}
.tile svg { width: 1.7rem; height: 1.7rem; flex: none; }
.tile:active { transform: translateY(3px); box-shadow: none; }

.qs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .4rem; }
.q {
  width: 100%; text-align: left; padding: .5rem .85rem; font-weight: 700; font-size: .9rem; line-height: 1.25;
  background: #fff; border: 3px solid var(--ink); border-radius: 16px; cursor: pointer; touch-action: manipulation;
  transition: background-color .12s, transform .08s;
}
.q:hover { background: var(--pink-wash); }
.q:active { transform: scale(.98); }

.how { border: 2px solid var(--line); border-radius: 14px; padding: .35rem .7rem; background: #fff; }
.how summary { cursor: pointer; font-weight: 700; }
.how ul { margin: .4rem 0 .2rem 1rem; padding: 0; display: flex; flex-direction: column; gap: .3rem; }
.how li::marker { color: var(--pink-deep); }

.actions { display: grid; grid-template-columns: 1fr 1fr; gap: .4rem; }
.act {
  display: inline-flex; align-items: center; justify-content: center; gap: .35rem; min-height: 2.2rem; padding: .25rem .5rem; text-align: center;
  background: transparent; color: var(--ink); border: 2px solid var(--line); border-radius: 999px; font-weight: 700; font-size: .8rem; line-height: 1.1; cursor: pointer;
}
.act:hover { background: var(--sky); border-color: var(--ink); }
.act svg { width: 1rem; height: 1rem; flex: none; }
.pill:focus-visible, .tile:focus-visible, .q:focus-visible, .act:focus-visible { outline: 3px solid var(--ink); outline-offset: 2px; box-shadow: 0 0 0 5px #fff; }
</style>
