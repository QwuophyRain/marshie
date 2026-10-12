<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarshmallowFace from './components/MarshmallowFace.vue'
import ChatPanel from './components/ChatPanel.vue'
import TeachDialog from './components/TeachDialog.vue'
import TeacherPanel from './components/TeacherPanel.vue'
import { settings } from './settings'
import { brand, bundledLogo, bundledWordmark, loadBrand } from './brand'
import { state, begin, poke, touch, SPEAKING_MOODS } from './composables/useMarshie'
import { loadCaps, mouth, stopSpeaking } from './composables/useVoice'

const teacherOpen = ref(false)
const fullscreen = ref(false)
const canFullscreen = typeof document !== 'undefined' && !!document.documentElement.requestFullscreen

const CAPTIONS = {
  idle: 'Hi! Ask me anything.',
  listening: 'I’m listening…',
  thinking: 'Let me think…',
  talking: 'Here’s what I know!',
  hello: 'Hello, friend!',
  love: 'Aww, thank you!',
  laugh: 'Hehe!',
  wow: 'Wow!',
  celebrate: 'Yay!',
  sad: 'Oh no, I’m sorry!',
  unsure: 'Hmm…',
  sleepy: 'Zzz… tap to wake me',
}
const faceMood = computed(() => (state.started ? state.mood : 'sleepy'))
const caption = computed(() => (state.started ? CAPTIONS[state.mood] : 'Zzz… I’m sleeping'))
const mouthLevel = computed(() => (SPEAKING_MOODS.includes(state.mood) ? mouth.value : null))
const headerLogo = computed(() => brand.logo || bundledWordmark)
const wakeLogo = computed(() => brand.logo || bundledLogo)

function toggleMute() {
  settings.voiceOn = !settings.voiceOn
  if (!settings.voiceOn) stopSpeaking()
}

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
    else await document.documentElement.requestFullscreen()
  } catch { /* the browser said no; nothing to do */ }
}
const onFullscreen = () => { fullscreen.value = !!document.fullscreenElement }

// Keep the screen on while Marshie is on show.
let wakeLock = null
async function keepAwake() {
  try {
    if (navigator.wakeLock && document.visibilityState === 'visible') wakeLock = await navigator.wakeLock.request('screen')
  } catch { /* not allowed (battery saver, old browser) */ }
}
const onVisible = () => { if (document.visibilityState === 'visible') keepAwake() }

watch(() => settings.bigText, (v) => document.documentElement.classList.toggle('big', !!v), { immediate: true })

function openTeacher() {
  stopSpeaking()
  teacherOpen.value = true
}

function tapMarshie() {
  if (state.started) poke()
  else begin()
}

onMounted(async () => {
  const h = await loadBrand()
  document.title = `${brand.name}, the ${brand.school} helper`
  loadCaps(h || undefined)
  keepAwake()
  document.addEventListener('visibilitychange', onVisible)
  document.addEventListener('fullscreenchange', onFullscreen)
  touch()
})
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', onVisible)
  document.removeEventListener('fullscreenchange', onFullscreen)
  try { wakeLock?.release() } catch { /* ignore */ }
})
</script>

<template>
  <div class="app" @pointerdown.passive="touch" @keydown="touch">
    <div class="ribbon" aria-hidden="true"></div>

    <header class="top">
      <div class="brand">
        <span class="logo-badge"><img :src="headerLogo" :alt="`${brand.school} logo`" /></span>
        <span class="brand-text">
          <h1>{{ brand.name }}</h1>
          <p>{{ brand.event }}</p>
        </span>
      </div>
      <div class="tools">
        <button class="btn small white" :aria-pressed="!settings.voiceOn" @click="toggleMute">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 9v6h4l5 4V5L8 9z" fill="currentColor" />
            <template v-if="settings.voiceOn"><path d="M16.500 8.500a5 5 0 010 7M19 6a8.500 8.500 0 010 12" /></template>
            <template v-else><path d="M16 9l5 6M21 9l-5 6" /></template>
          </svg>
          {{ settings.voiceOn ? 'Sound on' : 'Sound off' }}
        </button>
        <button v-if="canFullscreen" class="btn small white fs" @click="toggleFullscreen">
          {{ fullscreen ? 'Exit full screen' : 'Full screen' }}
        </button>
        <button class="btn small ghost" @click="openTeacher">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 018 0v3" />
          </svg>
          Teachers
        </button>
      </div>
    </header>

    <main class="stage">
      <section class="mascot" :aria-label="brand.name">
        <!-- the four dots from the school logo, drifting behind her -->
        <span class="dot d1" aria-hidden="true"></span>
        <span class="dot d2" aria-hidden="true"></span>
        <span class="dot d3" aria-hidden="true"></span>
        <span class="dot d4" aria-hidden="true"></span>
        <button class="face-wrap" @click="tapMarshie" :aria-label="state.started ? `Tickle ${brand.name}` : `Wake ${brand.name} up`">
          <MarshmallowFace :mood="faceMood" :mouth-level="mouthLevel" />
        </button>
        <p class="caption" aria-live="polite">{{ caption }}</p>
      </section>

      <section class="side">
        <div v-if="!state.started" class="wake">
          <img class="wake-logo" :src="wakeLogo" :alt="`${brand.school} bilingual school`" />
          <h2>Hello, friend!</h2>
          <p>I’m {{ brand.name }}, the helper for the {{ brand.school }} {{ brand.event }}. Ask me about maths, science, Ghana, art and lots more.</p>
          <button class="btn big-btn" @click="begin">Wake {{ brand.name }} up</button>
          <p class="hint">You can talk to me or type to me.</p>
        </div>
        <ChatPanel v-else />
      </section>
    </main>

    <TeachDialog v-if="state.teach" />
    <TeacherPanel v-if="teacherOpen" @close="teacherOpen = false" />
  </div>
</template>

<style scoped>
.app { height: 100%; display: flex; flex-direction: column; background: var(--sky); }

.top {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: .7rem 1.4rem .4rem;
}
.brand { display: flex; align-items: center; gap: .9rem; min-width: 0; }
.logo-badge {
  display: block; flex: none; height: 3.6rem; padding: .25rem .6rem; background: #fff;
  border: 3px solid var(--ink); border-radius: 16px; box-shadow: 0 4px 0 var(--ink);
}
.logo-badge img { display: block; height: 100%; width: auto; max-width: 11rem; object-fit: contain; }
.brand-text { display: flex; align-items: baseline; gap: .8rem; min-width: 0; padding-left: .9rem; border-left: 4px solid var(--brand); }
.brand h1 { font-size: 2.1rem; letter-spacing: .01em; color: var(--ink); font-variation-settings: 'wght' 800; }
.brand p { color: var(--ink-soft); font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tools { display: flex; align-items: center; gap: .7rem; flex-wrap: wrap; justify-content: flex-end; }

.stage {
  flex: 1; min-height: 0;
  display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 6fr); gap: 1.6rem;
  padding: 0 1.4rem 1.4rem;
}

.mascot { position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 0; gap: .6rem; }
.dot { position: absolute; border-radius: 50%; pointer-events: none; animation: drift 7s ease-in-out infinite; }
.dot.d1 { width: 1.7rem; height: 1.7rem; background: var(--green); left: 6%; top: 10%; }
.dot.d2 { width: 1.3rem; height: 1.3rem; background: var(--brand); right: 8%; top: 30%; animation-delay: -2s; animation-duration: 8s; }
.dot.d3 { width: 2.1rem; height: 2.1rem; background: var(--pink-deep); right: 12%; bottom: 14%; animation-delay: -4s; animation-duration: 6.5s; }
.dot.d4 { width: 1.5rem; height: 1.5rem; background: var(--gold); left: 9%; bottom: 20%; animation-delay: -1s; animation-duration: 9s; }
@keyframes drift { 0%, 100% { transform: translate(0, 0) } 33% { transform: translate(8px, -14px) } 66% { transform: translate(-7px, -5px) } }

.face-wrap {
  all: unset; display: block; cursor: pointer; position: relative;
  aspect-ratio: 400 / 470;
  width: min(100%, calc((100vh - 15rem) * 0.851));
  min-width: 11rem;
}
.face-wrap:focus-visible { outline: 4px solid var(--ink); outline-offset: 6px; border-radius: 40%; }
.caption {
  position: relative;
  font-family: var(--display); font-weight: 700; font-size: 1.7rem; text-align: center;
  min-height: 2.2rem; color: var(--ink);
}

.side { min-height: 0; display: flex; flex-direction: column; }

.wake {
  margin: auto; max-width: 30rem; text-align: center; padding: 1.6rem 2rem 2rem;
  background: var(--paper); border: 4px solid var(--ink); border-radius: 36px; box-shadow: 0 8px 0 var(--ink);
  display: flex; flex-direction: column; align-items: center; gap: 1rem;
}
.wake-logo { width: min(100%, 17rem); height: auto; border-radius: 14px; background: #fff; }
.wake h2 { font-size: 2.4rem; }
.wake p { font-size: 1.1rem; }
.big-btn { font-size: 1.5rem; min-height: 4.2rem; padding: .6rem 2.4rem; }

/* Portrait screens and phones: Marshie on top, chat below. */
@media (max-width: 900px), (orientation: portrait) {
  .app { height: auto; min-height: 100%; }
  .stage { grid-template-columns: 1fr; padding: 0 .9rem 1rem; gap: 1rem; }
  .face-wrap { width: min(62vw, 17rem, calc(34vh * 0.851)); min-width: 8rem; }
  .caption { font-size: 1.3rem; }
  .side { min-height: 70vh; }
  .brand h1 { font-size: 1.6rem; }
  .logo-badge { height: 2.9rem; }
  .top { padding: .5rem .9rem .3rem; }
  .brand p { display: none; }
  .brand-text { padding-left: .6rem; }
}
@media (max-width: 560px) {
  .top { flex-wrap: wrap; row-gap: .5rem; }
  .tools { width: 100%; justify-content: space-between; gap: .5rem; }
  .tools .fs { display: none; }                      /* full screen is for kiosks and laptops, not phones */
  .logo-badge img { max-width: 7rem; }
}
@media (prefers-reduced-motion: reduce) { .dot { animation: none; } }
</style>
