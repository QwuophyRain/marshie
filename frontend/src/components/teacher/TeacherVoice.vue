<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { applyVoiceStyle, resetSettings, settings } from '../../settings'
import { browserInfo, caps, isFancyVoice, listenAdvice, listenIssue, liveText, pickVoice, rankedVoices, speak, startListening, stopSpeaking } from '../../composables/useVoice'
import { logout } from '../../composables/useTeacher'

const voices = ref([])
const chosen = ref(null)
const testing = ref(false)
const fullscreenOk = typeof document !== 'undefined' && !!document.documentElement.requestFullscreen
const isMac = typeof navigator !== 'undefined' && /Mac/i.test(navigator.platform || navigator.userAgent || '')
const isWindows = typeof navigator !== 'undefined' && /Win/i.test(navigator.platform || navigator.userAgent || '')
const noFancy = computed(() => voices.value.length > 0 && !voices.value.some((x) => isFancyVoice(x.v)))

function refreshVoices() {
  voices.value = rankedVoices()
  chosen.value = pickVoice()
}
const custom = () => { settings.voiceStyle = 'custom' }

// ---- a button to try the microphone, with plain words about what went wrong
const browser = browserInfo()
const mic = ref({ state: '', heard: '', problem: '' })        // state: '' | 'listening' | 'done'
let stopMic = null
async function testMic() {
  if (mic.value.state === 'listening') { stopMic?.(); return }
  mic.value = { state: 'listening', heard: '', problem: '' }
  listenIssue.code = ''
  const l = startListening()
  stopMic = l.stop
  try {
    const text = await l.promise
    mic.value = { state: 'done', heard: text, problem: text ? '' : 'I did not hear any words. Press the button, then speak a little louder or closer to the microphone.' }
  } catch (e) {
    mic.value = { state: 'done', heard: '', problem: listenAdvice(listenIssue.code) || e.message }
  }
  stopMic = null
}
onBeforeUnmount(() => stopMic?.())
onMounted(() => {
  refreshVoices()
  if (caps.synth) window.speechSynthesis.addEventListener('voiceschanged', refreshVoices)
})
onBeforeUnmount(() => {
  if (caps.synth) window.speechSynthesis.removeEventListener('voiceschanged', refreshVoices)
  stopSpeaking()
})

async function test() {
  testing.value = true
  const was = settings.voiceOn
  settings.voiceOn = true
  try {
    await speak('Hello! I am Marshie, the marshmallow. Do you like my voice?')
  } finally {
    settings.voiceOn = was
    testing.value = false
  }
}

const LANGS = [
  ['en-GH', 'English (Ghana)'], ['en-NG', 'English (Nigeria)'], ['en-GB', 'English (UK)'], ['en-US', 'English (US)'],
]
const SLEEP = [[0, 'Never'], [30, 'After 30 seconds'], [45, 'After 45 seconds'], [90, 'After 90 seconds'], [180, 'After 3 minutes']]
const CLEAR = [[0, 'Never'], [1, 'After 1 minute'], [3, 'After 3 minutes'], [5, 'After 5 minutes'], [10, 'After 10 minutes']]

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
    else await document.documentElement.requestFullscreen()
  } catch { /* browser refused */ }
}
</script>

<template>
  <div class="tp-section">
    <h3>Voice and screen</h3>
    <p class="hint">These settings are saved on this screen only, so each computer can have its own.</p>

    <div class="tp-block">
      <h4>Marshie’s voice</h4>
      <label class="tp-check">
        <input v-model="settings.voiceOn" type="checkbox" />
        <span><b>Talk out loud</b><br /><span class="hint">When this is off she only types, and her mouth still moves.</span></span>
      </label>

      <fieldset class="styles">
        <legend class="lbl">How should she sound?</legend>
        <label class="style" :class="{ on: settings.voiceStyle === 'natural' }">
          <input type="radio" name="vstyle" :checked="settings.voiceStyle === 'natural'" @change="applyVoiceStyle('natural'); refreshVoices()" />
          <span><b>Natural</b><br /><span class="hint">Calm and clear, at a normal speed, like a phone assistant.</span></span>
        </label>
        <label class="style" :class="{ on: settings.voiceStyle === 'girl' }">
          <input type="radio" name="vstyle" :checked="settings.voiceStyle === 'girl'" @change="applyVoiceStyle('girl'); refreshVoices()" />
          <span><b>Young girl</b><br /><span class="hint">Higher and a little slower, like a cartoon marshmallow.</span></span>
        </label>
      </fieldset>
      <p v-if="settings.voiceStyle === 'custom'" class="hint">You have moved the sliders yourself. Pick a style above to go back to a ready-made voice.</p>

      <template v-if="caps.tts_server">
        <p class="tp-note good">Marshie is using the offline voice on this computer.</p>
        <div>
          <label class="lbl" for="v-sp">Pitch ({{ settings.serverPitch.toFixed(2) }}, 1.00 is natural)</label>
          <input id="v-sp" v-model.number="settings.serverPitch" type="range" min="0.9" max="1.5" step="0.02" @input="custom" />
          <p class="hint">Slide right for a smaller, higher voice. Slide left for a lower voice.</p>
        </div>
        <p class="hint">
          For a more lifelike offline voice, run <code>python3 marshie.py voice --piper-voice en_US-lessac-medium</code> (about 60 MB), then start her again.
        </p>
      </template>
      <template v-else>
        <p class="tp-note">Marshie is using the voice built into this browser. Which voices you can pick depends on this computer.</p>
        <div v-if="!caps.synth" class="tp-note bad">This browser has no speech voice. Try Chrome or Edge, or install the offline voice.</div>
        <template v-else>
          <p v-if="chosen" class="tp-note good" role="status">She is using <b>{{ chosen.name }}</b> ({{ chosen.lang }}).</p>
          <div>
            <label class="lbl" for="v-v">Voice</label>
            <select id="v-v" v-model="settings.voiceName" class="field" @change="refreshVoices">
              <option value="">{{ settings.voiceStyle === 'girl' ? 'Pick a girl’s voice for me' : 'Pick the most natural voice for me' }}</option>
              <option v-for="x in voices" :key="x.v.name + x.v.lang" :value="x.v.name">{{ x.v.name }} ({{ x.v.lang }}){{ isFancyVoice(x.v) ? ' ★' : '' }}</option>
            </select>
            <p class="hint">★ marks the most lifelike voices on this computer. The list is best first.</p>
          </div>
          <div>
            <label class="lbl" for="v-p">Pitch ({{ settings.pitch.toFixed(2) }}, 1.00 is natural)</label>
            <input id="v-p" v-model.number="settings.pitch" type="range" min="0.5" max="2" step="0.05" @input="custom" />
          </div>
          <div>
            <label class="lbl" for="v-r">Speed ({{ settings.rate.toFixed(2) }})</label>
            <input id="v-r" v-model.number="settings.rate" type="range" min="0.6" max="1.4" step="0.05" @input="custom" />
          </div>
          <details class="tip" :open="noFancy">
            <summary>{{ noFancy ? 'Get a more lifelike voice (recommended)' : 'Get an even more lifelike voice' }}</summary>
            <ul>
              <li v-if="isMac || !isWindows">
                <b>On a Mac:</b> open System Settings, Accessibility, Spoken Content, System Voice, Manage Voices. Download a voice marked
                <i>Premium</i> or <i>Enhanced</i> (for example Ava or Samantha), and any Siri voices you see. Then quit the browser fully and open it again.
              </li>
              <li v-if="isWindows || !isMac">
                <b>On Windows:</b> Microsoft Edge has the most lifelike voices (names ending in “Natural”, such as Aria or Jenny). Use Edge for the school screen.
              </li>
              <li><b>Anywhere, with no internet:</b> run <code>python3 marshie.py voice --piper-voice en_US-lessac-medium</code> to give her an offline voice.</li>
            </ul>
          </details>
        </template>
      </template>
      <div><button class="btn pink" :disabled="testing" @click="test">{{ testing ? 'Talking…' : 'Hear Marshie talk' }}</button></div>
    </div>

    <div class="tp-block">
      <h4>Talking back and forth</h4>
      <p class="hint">
        The <b>Talk with me</b> button under the chat starts a conversation: she listens, answers out loud, then listens again.
        Children can say “stop” or “goodbye” to end it, or tap Marshie while she talks to interrupt her. She only listens when she is not talking, so she never hears herself.
      </p>
      <label class="tp-check">
        <input v-model="settings.autoTalk" type="checkbox" />
        <span><b>Start chatting by herself when she wakes up</b><br /><span class="hint">Good for a school screen. Otherwise children press <b>Talk with me</b>.</span></span>
      </label>
      <label class="tp-check">
        <input v-model="settings.chime" type="checkbox" />
        <span><b>Play a soft sound when she starts listening</b><br /><span class="hint">It tells children it is their turn to speak.</span></span>
      </label>
    </div>

    <div class="tp-block">
      <h4>Listening</h4>
      <p v-if="caps.stt_server" class="tp-note good">Marshie is using the offline listener on this computer. It works without the internet.</p>
      <p v-else-if="caps.recognition && caps.secure" class="tp-note">Marshie is using the browser’s speech recognition. It works in Chrome and Edge and needs the internet.</p>
      <p v-else-if="!caps.secure" class="tp-note bad">The microphone only works on a secure address. Open Marshie at <code>http://localhost:8000</code> on this computer, or publish her online (which uses HTTPS).</p>
      <p v-else class="tp-note bad">This browser cannot listen. Children can still type, or you can use Chrome or Edge.</p>
      <p v-if="!caps.stt_server && browser.note && mic.problem !== browser.note" class="tp-note bad">You are using {{ browser.name }}. {{ browser.note }}</p>

      <div>
        <button type="button" class="btn pink tp-fit" :class="{ rec: mic.state === 'listening' }" @click="testMic">
          {{ mic.state === 'listening' ? 'Listening… press to stop' : 'Test the microphone' }}
        </button>
        <p v-if="mic.state === 'listening'" class="hint" aria-live="polite">Say something now.<template v-if="liveText"> I hear: “{{ liveText }}”</template></p>
        <p v-else-if="mic.heard" class="tp-note good" role="status">It works. I heard: “{{ mic.heard }}”</p>
        <p v-else-if="mic.problem" class="tp-note bad" role="alert">{{ mic.problem }}</p>
      </div>

      <details v-if="!caps.stt_server" class="tip" :open="!!(mic.problem || listenIssue.code)">
        <summary>Make listening work without the internet (any browser)</summary>
        <p class="hint">
          If the test above fails, or you want listening that never depends on the internet, give Marshie her own ears. In the Terminal
          (or Warp) on this computer:
        </p>
        <ol>
          <li>Press <b>Ctrl+C</b> to stop Marshie.</li>
          <li>Run <code>python3 marshie.py voice --only listen</code>. It downloads a small English listening model (about 40 MB) once.</li>
          <li>Run <code>python3 marshie.py start</code> and open her again. This tab will then say she is using the offline listener.</li>
        </ol>
        <p class="hint">
          Clear speech works best, and the words appear after the child stops speaking instead of while they speak.
          The browser’s own service is a little more accurate when it works.
        </p>
      </details>

      <div v-if="!caps.stt_server">
        <label class="lbl" for="v-l">The way children speak</label>
        <select id="v-l" v-model="settings.lang" class="field">
          <option v-for="[code, label] in LANGS" :key="code" :value="code">{{ label }}</option>
        </select>
        <p class="hint">If listening does not work with Ghana English, choose UK or US English.</p>
      </div>
    </div>

    <div class="tp-block">
      <h4>Screen</h4>
      <label class="tp-check">
        <input v-model="settings.bigText" type="checkbox" />
        <span><b>Bigger writing</b><br /><span class="hint">Helpful for a projector or a screen far from the children.</span></span>
      </label>
      <div class="tp-row">
        <div>
          <label class="lbl" for="v-sl">Marshie falls asleep</label>
          <select id="v-sl" v-model.number="settings.sleepSeconds" class="field">
            <option v-for="[n, label] in SLEEP" :key="n" :value="n">{{ label }}</option>
          </select>
        </div>
        <div>
          <label class="lbl" for="v-cl">Start a fresh chat when nobody is there</label>
          <select id="v-cl" v-model.number="settings.autoClearMinutes" class="field">
            <option v-for="[n, label] in CLEAR" :key="n" :value="n">{{ label }}</option>
          </select>
        </div>
      </div>
      <div class="tp-row">
        <button v-if="fullscreenOk" class="btn white tp-fit" @click="toggleFullscreen">Full screen on or off</button>
        <button class="btn white tp-fit" @click="resetSettings">Put everything back</button>
      </div>
    </div>

    <div class="tp-block">
      <h4>Teacher PIN</h4>
      <p class="hint">The PIN is set in the <code>.env</code> file on the computer that runs Marshie, so children cannot change it from here.</p>
      <div><button class="btn white" @click="logout()">Lock the teacher panel</button></div>
    </div>
  </div>
</template>

<style scoped>
.styles { border: 0; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: .7rem; }
.styles legend { padding: 0; margin-bottom: .5rem; }
.style { display: flex; gap: .7rem; align-items: flex-start; padding: .7rem .9rem; border: 3px solid var(--ink); border-radius: 18px; cursor: pointer; background: #fff; }
.style.on { background: var(--pink-wash); box-shadow: 0 4px 0 var(--ink); }
.style input { width: 1.4rem; height: 1.4rem; margin-top: .2rem; accent-color: var(--pink-deep); flex: none; }
.tip { border: 2px solid var(--line); border-radius: 14px; padding: .6rem .9rem; background: var(--paper); }
.tip summary { cursor: pointer; font-weight: 700; }
.tip ul, .tip ol { margin: .5rem 0 0 1.3rem; padding: 0; display: flex; flex-direction: column; gap: .5rem; }
.rec { background: var(--berry); color: #fff; }
</style>
