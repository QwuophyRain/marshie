<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { api } from '../../api'
import { brand, bundledLogo, loadBrand, previewTheme, setTheme } from '../../brand'
import { guard, loadOverview, overview, say } from '../../composables/useTeacher'
import { speak } from '../../composables/useVoice'
import { SCHOOL_COLOURS, applyTheme, isHex, paletteFromImage } from '../../theme'
import MarshmallowFace from '../MarshmallowFace.vue'

// ------------------------------------------------------------------ greeting
const defaultGreeting = computed(() => overview.value?.defaults?.greeting || brand.greeting)
const greeting = ref(overview.value?.settings?.greeting || defaultGreeting.value)
const filled = computed(() => greeting.value.replaceAll('{name}', brand.name).replaceAll('{school}', brand.school))
const saving = ref(false)

async function saveGreeting(hear = false) {
  saving.value = true
  const text = greeting.value.trim()
  const res = await guard(() => api.setSettings({ greeting: text === defaultGreeting.value ? '' : text }))
  saving.value = false
  if (!res) return
  await Promise.all([loadBrand(), loadOverview()])
  say('Saved. This is what Marshie says when she wakes up.')
  if (hear) speak(brand.greetingSpoken || brand.greeting)
}
async function standardGreeting() {
  greeting.value = defaultGreeting.value
  await saveGreeting()
}

// ------------------------------------------------------------------ colours
const ROLES = [
  { id: 'primary', label: 'Main colour', hint: 'Text, outlines, the page wash, the dotted ribbon' },
  { id: 'button', label: 'Button colour', hint: 'The big buttons, like “Wake Marshie up”' },
  { id: 'highlight', label: 'Highlight colour', hint: 'Marshie’s bow, selected tabs, cheeks' },
  { id: 'success', label: 'Good-job colour', hint: '“That’s right”, Add buttons, confetti' },
]
const draft = reactive({ ...SCHOOL_COLOURS, ...brand.theme })
const changed = computed(() => ROLES.some((r) => draft[r.id].toLowerCase() !== (brand.theme[r.id] || '').toLowerCase()))
const isSchool = computed(() => ROLES.every((r) => draft[r.id].toLowerCase() === SCHOOL_COLOURS[r.id]))

function tryColours() { previewTheme(draft) }
function setHex(role, value) {
  const v = value.trim().startsWith('#') ? value.trim() : '#' + value.trim()
  if (isHex(v)) { draft[role] = v.toLowerCase(); tryColours() }
}
async function saveColours() {
  const res = await guard(() => api.setSettings({ theme: { ...draft } }))
  if (!res) return
  setTheme(res.theme || draft)
  await loadOverview()
  say('Saved. Everyone sees these colours now.')
}
async function backToSchool() {
  Object.assign(draft, SCHOOL_COLOURS)
  const res = await guard(() => api.setSettings({ theme: {} }))
  if (!res) return
  setTheme(res.theme || SCHOOL_COLOURS)
  say('Back to the Ecole Ronsard colours.')
}
onBeforeUnmount(() => applyTheme(brand.theme))          // colours you tried but did not save go away

// ------------------------------------------------------------------ logo
const shownLogo = computed(() => brand.logo || bundledLogo)
const busyLogo = ref(false)
const palette = ref(null)

async function chooseLogo(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  busyLogo.value = true
  const res = await guard(() => api.setLogo(file))
  busyLogo.value = false
  if (res) { await loadBrand(); say('Logo changed. It shows at the top of the screen.') }
}
async function removeLogo() {
  if (await guard(() => api.removeLogo())) { await loadBrand(); say('Using the Ecole Ronsard logo again.') }
}
async function coloursFromLogo() {
  busyLogo.value = true
  try {
    const p = await paletteFromImage(shownLogo.value)
    if (!p) { say('I could not find clear colours in that logo. Pick them by hand instead.', true); return }
    Object.assign(draft, p)
    tryColours()
    palette.value = p
    say('I picked these colours from the logo. Try them, then press Save colours.')
  } catch (e) {
    say(e.message, true)
  } finally {
    busyLogo.value = false
  }
}

// ------------------------------------------------------------------ her faces
const FACES = [
  ['idle', 'Smiling'], ['hello', 'Waving hello'], ['listening', 'Listening'], ['thinking', 'Thinking'],
  ['talking', 'Talking'], ['love', 'Thank you'], ['laugh', 'Giggling'], ['wow', 'Amazed'],
  ['celebrate', 'Celebrating'], ['sad', 'Sorry'], ['unsure', 'Puzzled'], ['sleepy', 'Sleepy'],
]
</script>

<template>
  <div class="tp-section">
    <h3>Look and words</h3>

    <div class="tp-block">
      <h4>What Marshie says when she wakes up</h4>
      <p class="hint">Write <code>{name}</code> where her name goes and <code>{school}</code> where the school’s name goes.</p>
      <label class="lbl" for="g-text">Greeting</label>
      <textarea id="g-text" v-model="greeting" class="field" rows="4" maxlength="700"></textarea>
      <p class="preview" aria-live="polite"><b>Preview:</b> {{ filled }}</p>
      <div class="tp-row">
        <button class="btn green tp-fit" :disabled="saving || greeting.trim().length < 5" @click="saveGreeting(true)">Save and hear it</button>
        <button class="btn white tp-fit" :disabled="saving || greeting.trim() === defaultGreeting" @click="standardGreeting">Use the standard greeting</button>
      </div>
    </div>

    <div class="tp-block">
      <h4>School colours</h4>
      <p class="hint">Colours change on this screen straight away. Press <b>Save colours</b> to keep them for everyone.</p>
      <ul class="swatches tp-list">
        <li v-for="r in ROLES" :key="r.id" class="swatch">
          <input :id="`c-${r.id}`" type="color" :value="draft[r.id]" :aria-label="r.label" @input="(e) => { draft[r.id] = e.target.value; tryColours() }" />
          <div class="txt">
            <label :for="`c-${r.id}`"><b>{{ r.label }}</b></label>
            <span class="hint">{{ r.hint }}</span>
          </div>
          <input class="field hex" type="text" :value="draft[r.id]" maxlength="7" :aria-label="`${r.label} as a hex code`" @change="(e) => setHex(r.id, e.target.value)" />
        </li>
      </ul>
      <div class="tp-row">
        <button class="btn green tp-fit" :disabled="!changed" @click="saveColours">Save colours</button>
        <button class="btn white tp-fit" :disabled="isSchool && !changed && !overview?.settings?.theme?.primary" @click="backToSchool">Use the Ecole Ronsard colours</button>
      </div>
    </div>

    <div class="tp-block">
      <h4>School logo</h4>
      <div class="logo-row">
        <img class="logo" :src="shownLogo" :alt="`${brand.school} logo`" />
        <div class="logo-actions">
          <p class="hint">{{ brand.logo ? 'You added this logo.' : 'This is the Ecole Ronsard logo that comes with Marshie.' }}</p>
          <label class="btn white tp-fit">
            {{ busyLogo ? 'Working…' : 'Use a different logo' }}
            <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" class="sr-only" @change="chooseLogo" />
          </label>
          <button class="btn white tp-fit" :disabled="busyLogo" @click="coloursFromLogo">Pick the colours from this logo</button>
          <button v-if="brand.logo" class="btn white tp-fit" @click="removeLogo">Go back to the Ecole Ronsard logo</button>
        </div>
      </div>
      <p v-if="palette" class="hint">Colours found: <span v-for="(c, k) in palette" :key="k" class="chip-dot" :style="{ background: c }" :title="k"></span></p>
    </div>

    <div class="tp-block">
      <h4>Marshie’s faces</h4>
      <p class="hint">She shows how she feels. Tap her in the chat and she giggles, waves, gasps or blushes.</p>
      <ul class="faces tp-list">
        <li v-for="[id, label] in FACES" :key="id" class="face">
          <div class="art"><MarshmallowFace :mood="id" :antics="false" /></div>
          <span>{{ label }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.preview { padding: .6rem .9rem; background: var(--pink-wash); border: 2px solid var(--line); border-radius: 14px; overflow-wrap: anywhere; }
.swatches { gap: .6rem; }
.swatch { display: flex; align-items: center; gap: .9rem; padding: .5rem .8rem; border: 2px solid var(--line); border-radius: 16px; background: var(--paper); flex-wrap: wrap; }
.swatch input[type='color'] { width: 3.4rem; height: 3.4rem; padding: 0; border: 3px solid var(--ink); border-radius: 14px; background: #fff; cursor: pointer; flex: none; }
.swatch .txt { flex: 1 1 12rem; display: flex; flex-direction: column; min-width: 0; }
.hex { width: 8rem; flex: none; font-family: ui-monospace, Menlo, Consolas, monospace; }
.logo-row { display: flex; gap: 1.2rem; flex-wrap: wrap; align-items: center; }
.logo { width: min(100%, 16rem); height: auto; border: 3px solid var(--ink); border-radius: 16px; background: #fff; }
.logo-actions { display: flex; flex-direction: column; gap: .6rem; align-items: flex-start; }
label.btn:focus-within { outline: 4px solid var(--ink); outline-offset: 3px; }
.chip-dot { display: inline-block; width: 1.6rem; height: 1.6rem; border-radius: 50%; border: 2px solid var(--ink); margin-right: .4rem; vertical-align: middle; }
.faces { display: grid; grid-template-columns: repeat(auto-fill, minmax(8.5rem, 1fr)); gap: .8rem; }
.face { display: flex; flex-direction: column; align-items: center; gap: .3rem; padding: .6rem .4rem 1rem; border: 2px solid var(--line); border-radius: 16px; background: var(--paper); font-weight: 700; text-align: center; }
.face .art { width: 6.4rem; aspect-ratio: 400 / 470; }
</style>
