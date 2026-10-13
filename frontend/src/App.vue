<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarshmallowFace from './components/MarshmallowFace.vue'
import AnswerCard from './components/AnswerCard.vue'
import Dock from './components/Dock.vue'
import MenuBox from './components/MenuBox.vue'
import HistorySheet from './components/HistorySheet.vue'
import TeachDialog from './components/TeachDialog.vue'
import TeacherPanel from './components/TeacherPanel.vue'
import { settings } from './settings'
import { brand, bundledLogo, bundledWordmark, loadBrand, loadGreeting } from './brand'
import { LANGUAGE_LIST, lang, t } from './i18n'
import { ui, closePanels } from './ui'
import { state, begin, poke, touch, setLanguage, stopQuiz, SPEAKING_MOODS } from './composables/useMarshie'
import { loadCaps, mouth, stopSpeaking } from './composables/useVoice'

const teacherOpen = ref(false)
const menuBtn = ref(null)

const faceMood = computed(() => (state.started ? state.mood : 'sleepy'))
const caption = computed(() => (state.started ? t(`cap.${state.mood}`) : t('cap.asleep')))
const mouthLevel = computed(() => (SPEAKING_MOODS.includes(state.mood) ? mouth.value : null))
const headerLogo = computed(() => brand.logo || bundledWordmark)
const wakeLogo = computed(() => brand.logo || bundledLogo)

function toggleMute() {
  settings.voiceOn = !settings.voiceOn
  if (!settings.voiceOn) stopSpeaking()
}
function toggleMenu() {
  touch()
  ui.history = false
  ui.menu = !ui.menu
}

// Keep the screen on while Marshie is on show.
let wakeLock = null
async function keepAwake() {
  try {
    if (navigator.wakeLock && document.visibilityState === 'visible') wakeLock = await navigator.wakeLock.request('screen')
  } catch { /* not allowed (battery saver, old browser) */ }
}
const onVisible = () => { if (document.visibilityState === 'visible') keepAwake() }

watch(() => settings.bigText, (v) => document.documentElement.classList.toggle('big', !!v), { immediate: true })
watch(() => settings.language, (code) => { try { document.documentElement.lang = code } catch { /* no document */ } }, { immediate: true })

function openTeacher() {
  stopSpeaking()
  closePanels()
  teacherOpen.value = true
}

function tapMarshie() {
  closePanels()
  if (state.started) poke()
  else begin()
}

// a tap anywhere outside the small menu closes it
function onPointer(e) {
  touch()
  if (ui.menu && !e.target.closest?.('.menu, .menu-btn')) ui.menu = false
}
function onEsc() {
  if (ui.zoom) ui.zoom = null
  else if (ui.history) ui.history = false
  else if (ui.menu) ui.menu = false
}
watch(() => ui.menu, async (open) => {
  if (open) return
  await nextTick()
  if (document.activeElement === document.body) menuBtn.value?.focus({ preventScroll: true })
})

onMounted(async () => {
  loadGreeting(settings.language)
  const h = await loadBrand()
  document.title = `${brand.name}, the ${brand.school} helper`
  loadCaps(h || undefined)
  keepAwake()
  document.addEventListener('visibilitychange', onVisible)
  touch()
})
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisible)
  try { wakeLock?.release() } catch { /* ignore */ }
})
</script>

<template>
  <div
    class="app" :class="{ asleep: !state.started, teaching: !!state.teach }"
    @pointerdown.passive="onPointer" @keydown="touch" @keydown.esc="onEsc"
  >
    <div class="ribbon" aria-hidden="true"></div>

    <main class="stage">
      <!-- the four dots from the school logo, drifting behind her -->
      <span class="dot d1" aria-hidden="true"></span>
      <span class="dot d2" aria-hidden="true"></span>
      <span class="dot d3" aria-hidden="true"></span>
      <span class="dot d4" aria-hidden="true"></span>

      <!-- Marshie fills the screen -->
      <div class="figure">
        <button
          class="face-wrap" :aria-label="state.started ? t('face.tickle', { name: brand.name }) : t('face.wake', { name: brand.name })"
          @click="tapMarshie"
        >
          <MarshmallowFace :mood="faceMood" :mouth-level="mouthLevel" :gender="settings.voiceGender" />
        </button>
      </div>

      <header class="top">
        <div class="brand">
          <span class="logo-badge"><img :src="headerLogo" :alt="`${brand.school} logo`" /></span>
          <span class="brand-text">
            <h1>{{ brand.name }}</h1>
            <p>{{ brand.event }}</p>
          </span>
        </div>
        <div class="tools">
          <button class="round" :aria-label="settings.voiceOn ? t('menu.soundOn') : t('menu.soundOff')" :title="settings.voiceOn ? t('menu.soundOn') : t('menu.soundOff')" @click="toggleMute">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4 9v6h4l5 4V5L8 9z" fill="currentColor" />
              <template v-if="settings.voiceOn"><path d="M16.500 8.500a5 5 0 010 7M19 6a8.500 8.500 0 010 12" /></template>
              <template v-else><path d="M16 9l5 6M21 9l-5 6" /></template>
            </svg>
          </button>
          <button ref="menuBtn" class="btn small white menu-btn" :aria-expanded="ui.menu" aria-haspopup="dialog" @click="toggleMenu">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
            {{ t('menu.open') }}
          </button>
        </div>
      </header>

      <!-- how she feels, in words; during a quiz it shows the score -->
      <div v-if="state.quiz" class="status quiz" role="status">
        <span :title="t('quiz.bar', { score: state.quiz.score, total: state.quiz.total })">{{ t('quiz.barShort', { score: state.quiz.score, total: state.quiz.total }) }}</span>
        <button type="button" class="btn small white" @click="stopQuiz">{{ t('quiz.stop') }}</button>
      </div>
      <p v-else class="status" aria-live="polite">{{ caption }}</p>

      <AnswerCard v-if="state.started && !state.teach" />

      <section v-else-if="!state.started" class="wake" :aria-label="brand.name">
        <img class="wake-logo" :src="wakeLogo" :alt="brand.school" />
        <h2>{{ t('wake.title') }}</h2>
        <p class="intro">{{ t('wake.intro', { name: brand.name, school: brand.school, event: brand.event }) }}</p>
        <button class="btn big-btn" @click="begin">{{ t('wake.button', { name: brand.name }) }}</button>
        <div class="langs" role="group" :aria-label="t('wake.language')">
          <button
            v-for="l in LANGUAGE_LIST" :key="l.code" type="button" class="lang" :class="{ on: lang() === l.code }"
            :aria-pressed="lang() === l.code" :lang="l.code" @click="setLanguage(l.code)"
          >{{ l.native }}</button>
        </div>
        <p class="hint">{{ t('wake.hint') }}</p>
      </section>

      <MenuBox v-if="ui.menu" @teachers="openTeacher" />
      <HistorySheet v-if="ui.history" />
    </main>

    <Dock v-if="state.started" />

    <div v-if="ui.zoom" class="lightbox" role="dialog" aria-modal="true" :aria-label="ui.zoom.title" @click="ui.zoom = null">
      <img :src="ui.zoom.url" :alt="ui.zoom.title" />
      <p>{{ ui.zoom.title }}</p>
      <button class="btn small white" type="button" autofocus @click.stop="ui.zoom = null">{{ t('menu.close') }}</button>
    </div>

    <TeachDialog v-if="state.teach" />
    <TeacherPanel v-if="teacherOpen" @close="teacherOpen = false" />
  </div>
</template>

<style scoped>
.app {
  height: 100%; height: 100dvh; display: grid; grid-template-rows: 18px minmax(0, 1fr) auto;
  background: var(--sky); overflow: hidden;
}

/* ---------------------------------------------------------------- the stage: Marshie takes all of it */
.stage {
  position: relative; min-height: 0; overflow: hidden; container-type: size;
  background: radial-gradient(ellipse 46% 60% at 50% 52%, rgba(255, 255, 255, .7), rgba(255, 255, 255, 0) 100%);
}

.figure {
  position: absolute; inset: 0; display: flex; justify-content: center; align-items: center;
  padding: 3.8rem var(--shift, 0px) 0 0; transition: padding-right .5s cubic-bezier(.3, 1, .4, 1);
}
.face-wrap {
  all: unset; position: relative; flex: none; display: block; cursor: pointer;
  aspect-ratio: 400 / 470; height: 100%; max-width: 100%;
  height: min(100%, calc((100cqw - var(--shift, 0px)) * 1.175));
  transition: height .5s cubic-bezier(.3, 1, .4, 1);
}
.face-wrap:focus-visible { outline: 4px solid var(--ink); outline-offset: -6px; border-radius: 40%; }

.dot { position: absolute; border-radius: 50%; pointer-events: none; animation: drift 7s ease-in-out infinite; }
.dot.d1 { width: 1.7rem; height: 1.7rem; background: var(--green); left: 7%; top: 26%; }
.dot.d2 { width: 1.3rem; height: 1.3rem; background: var(--brand); right: 9%; top: 34%; animation-delay: -2s; animation-duration: 8s; }
.dot.d3 { width: 2.1rem; height: 2.1rem; background: var(--pink-deep); right: 12%; bottom: 30%; animation-delay: -4s; animation-duration: 6.5s; }
.dot.d4 { width: 1.5rem; height: 1.5rem; background: var(--gold); left: 10%; bottom: 36%; animation-delay: -1s; animation-duration: 9s; }
@keyframes drift { 0%, 100% { transform: translate(0, 0) } 33% { transform: translate(8px, -14px) } 66% { transform: translate(-7px, -5px) } }

/* ---------------------------------------------------------------- the top row, floating over the stage */
.top {
  position: absolute; z-index: 5; top: 0; left: 0; right: 0; display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;
  padding: .8rem 1.1rem 0; pointer-events: none;
}
.top > * { pointer-events: auto; }
.brand { display: flex; align-items: center; gap: .8rem; min-width: 0; }
.logo-badge {
  display: block; flex: none; height: 3.3rem; padding: .22rem .55rem; background: #fff;
  border: 3px solid var(--ink); border-radius: 15px; box-shadow: 0 4px 0 var(--ink);
}
.logo-badge img { display: block; height: 100%; width: auto; max-width: 10rem; object-fit: contain; }
.brand-text { display: flex; align-items: baseline; gap: .8rem; min-width: 0; padding: .25rem 0 .25rem .8rem; border-left: 4px solid var(--brand); }
.brand h1 { font-size: 1.9rem; letter-spacing: .01em; color: var(--ink); font-variation-settings: 'wght' 800; }
.brand p { color: var(--ink-soft); font-weight: 700; white-space: nowrap; }
.tools { display: flex; align-items: center; gap: .6rem; }
.round {
  display: grid; place-items: center; width: 2.4rem; height: 2.4rem; padding: 0; cursor: pointer;
  background: #fff; color: var(--ink); border: 3px solid var(--ink); border-radius: 50%; box-shadow: 0 4px 0 var(--ink);
  transition: transform .08s, box-shadow .08s; touch-action: manipulation;
}
.round:active { transform: translateY(4px); box-shadow: none; }
.round svg { width: 1.3rem; height: 1.3rem; }

/* how she feels, as a pill at the top centre */
.status {
  position: absolute; z-index: 4; top: .95rem; left: calc((100% - var(--shift, 0px)) / 2); transform: translateX(-50%);
  transition: left .5s cubic-bezier(.3, 1, .4, 1); width: max-content; max-width: min(26rem, calc(100% - 22rem)); padding: .35rem 1.1rem;
  font-family: var(--display); font-weight: 700; font-size: 1.3rem; line-height: 1.2; text-align: center;
  background: #fff; border: 3px solid var(--ink); border-radius: 999px; box-shadow: 0 4px 0 var(--ink);
}
.status.quiz { display: flex; align-items: center; gap: .7rem; padding: .2rem .3rem .2rem 1.1rem; background: var(--note); white-space: nowrap; }

/* ---------------------------------------------------------------- asleep: the wake-up card */
.wake {
  position: absolute; z-index: 3; left: 50%; bottom: clamp(.6rem, 3cqh, 1.6rem); transform: translateX(-50%);
  width: min(30rem, calc(100% - 1.4rem)); max-height: calc(100% - 1.2rem); overflow-y: auto;
  padding: 1.1rem 1.6rem 1.2rem; text-align: center;
  background: var(--paper); border: 4px solid var(--ink); border-radius: 32px; box-shadow: 0 8px 0 var(--ink);
  display: flex; flex-direction: column; align-items: center; gap: .75rem;
}
.wake-logo { width: min(100%, 13rem); height: auto; border-radius: 14px; background: #fff; }
.wake h2 { font-size: 2.1rem; }
.wake .intro { font-size: 1.05rem; }
.big-btn { font-size: 1.45rem; min-height: 4rem; padding: .5rem 2.2rem; }
.langs { display: flex; flex-wrap: wrap; justify-content: center; gap: .45rem; }
.lang {
  min-height: 2.5rem; padding: .25rem 1rem; background: #fff; color: var(--ink); cursor: pointer;
  border: 3px solid var(--ink); border-radius: 999px; font-weight: 700; font-size: .95rem; touch-action: manipulation;
  transition: background-color .12s, transform .08s;
}
.lang:active { transform: scale(.96); }
.lang.on { background: var(--gold); color: var(--on-gold); box-shadow: 0 3px 0 var(--ink); }

/* ---------------------------------------------------------------- picture lightbox */
.lightbox {
  position: fixed; inset: 0; z-index: 40; background: rgba(2, 35, 45, .88); display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: .8rem; padding: 1rem; cursor: zoom-out;
}
.lightbox img { max-width: 100%; max-height: calc(100% - 7rem); object-fit: contain; background: #fff; border-radius: 16px; border: 4px solid #fff; }
.lightbox p { color: #fff; font-weight: 700; font-size: 1.15rem; text-align: center; }

/* ---------------------------------------------------------------- wide landscape: beside her, not over her */
@media (min-width: 901px) and (orientation: landscape) {
  .app.asleep { --shift: min(34rem, 42cqw); }
  .app.teaching { --shift: min(36rem, 54cqw); }
  .app.asleep .brand-text, .app.teaching .brand-text { display: none; }      /* her caption moves over her, so the name makes room */
  .wake { left: auto; right: 1.4rem; bottom: auto; top: 50%; transform: translateY(-50%); }
}
@media (max-width: 1499px) { .brand p { display: none; } }
@media (max-width: 1099px) { .brand-text { display: none; } }

/* ---------------------------------------------------------------- portrait screens and phones: the caption sits under the top row */
@media (max-width: 900px), (orientation: portrait) {
  .figure { align-items: flex-start; padding: 7.6rem 0 0; }
  .status { top: 4.5rem; max-width: calc(100% - 1.4rem); font-size: 1.05rem; padding: .3rem .95rem; }
  .brand h1 { font-size: 1.6rem; }
  .logo-badge { height: 2.9rem; }
  .top { padding: .65rem .8rem 0; }
  .brand-text { display: flex; }
  .brand p { display: none; }
  .wake { left: 50%; right: auto; top: auto; bottom: clamp(.6rem, 3cqh, 1.6rem); transform: translateX(-50%); padding: .9rem 1.2rem 1rem; gap: .55rem; }
  .wake-logo { display: none; }
  .wake h2 { font-size: 1.7rem; }
  .wake .intro { font-size: 1rem; }
  .big-btn { font-size: 1.25rem; min-height: 3.6rem; padding-inline: 1.8rem; }
}
@media (max-width: 560px) {
  .brand-text { display: none; }
  .logo-badge img { max-width: 7.5rem; }
  .wake .hint { display: none; }
}
@media (max-height: 800px) { .wake-logo { display: none; } }          /* the logo is already in the top corner */
@media (max-height: 520px) {
  .wake .intro, .wake .hint { display: none; }
}
/* a short wide screen (a laptop, a Pi kiosk): keep a strip under her for the answer card, so her mouth stays in view */
@media (min-width: 901px) and (orientation: landscape) and (max-height: 780px) {
  .app:not(.asleep) .figure { padding-bottom: 9cqh; }
}
@media (prefers-reduced-motion: reduce) { .dot { animation: none; } }
</style>
