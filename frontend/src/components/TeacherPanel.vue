<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import '../teacher.css'
import { api } from '../api'
import {
  authed, loginNote, overview, toast, signedIn, logout, loadOverview, teachPrefill,
} from '../composables/useTeacher'
import TeacherToday from './teacher/TeacherToday.vue'
import TeacherAdd from './teacher/TeacherAdd.vue'
import TeacherExcel from './teacher/TeacherExcel.vue'
import TeacherLook from './teacher/TeacherLook.vue'
import TeacherAI from './teacher/TeacherAI.vue'
import TeacherTeach from './teacher/TeacherTeach.vue'
import TeacherLibrary from './teacher/TeacherLibrary.vue'
import TeacherVoice from './teacher/TeacherVoice.vue'

const emit = defineEmits(['close'])

const TABS = [
  { id: 'today', label: 'Today' },
  { id: 'add', label: 'Add data' },
  { id: 'excel', label: 'Excel sheets' },
  { id: 'teach', label: 'Teach by typing' },
  { id: 'library', label: 'What Marshie knows' },
  { id: 'look', label: 'Look and words' },
  { id: 'ai', label: 'Paid AI' },
  { id: 'voice', label: 'Voice and screen' },
]
const tab = ref('today')
const pin = ref('')
const pinBox = ref(null)
const error = ref('')
const working = ref(false)
const pane = ref(null)

const pendingCount = computed(() => overview.value?.stats?.pending || 0)

async function login() {
  error.value = ''
  working.value = true
  try {
    const res = await api.login(pin.value.trim())
    signedIn(res.token)
    pin.value = ''
    await loadOverview()
  } catch (e) {
    error.value = e.message
    pin.value = ''
  } finally {
    working.value = false
  }
}

function teachThis(question) {
  teachPrefill.value = question
  tab.value = 'teach'
}

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}

watch(tab, async () => { await nextTick(); pane.value?.scrollTo({ top: 0 }) })
watch(authed, async (v) => {
  if (!v) { await nextTick(); pinBox.value?.focus() }
})
onMounted(async () => {
  if (authed.value) loadOverview()
  else pinBox.value?.focus()
})
</script>

<template>
  <div class="tp" role="dialog" aria-modal="true" aria-labelledby="tp-title" @keydown="onKey">
    <div class="ribbon" aria-hidden="true"></div>
    <header class="bar">
      <h2 id="tp-title">Teacher panel</h2>
      <div class="bar-btns">
        <button v-if="authed" class="btn small white" @click="logout(); emit('close')">Lock and close</button>
        <button class="btn small" @click="emit('close')">Back to Marshie</button>
      </div>
    </header>

    <div v-if="!authed" class="login-wrap">
      <form class="login" @submit.prevent="login">
        <h3>Teachers only</h3>
        <p>Type the teacher PIN to teach Marshie, add Excel sheets, pictures and recordings, and change settings.</p>
        <label class="lbl" for="pin">Teacher PIN</label>
        <input id="pin" ref="pinBox" v-model="pin" class="field" type="password" inputmode="numeric" autocomplete="current-password" />
        <p v-if="loginNote && !error" class="tp-note">{{ loginNote }}</p>
        <p v-if="error" class="tp-note bad" role="alert">{{ error }}</p>
        <button class="btn green" type="submit" :disabled="!pin.trim() || working">Open</button>
      </form>
    </div>

    <template v-else>
      <nav class="tabs" role="tablist" aria-label="Teacher panel sections">
        <button
          v-for="t in TABS" :id="`tab-${t.id}`" :key="t.id" role="tab" class="tab" :class="{ on: tab === t.id }"
          :aria-selected="tab === t.id" :aria-controls="`pane-${t.id}`" @click="tab = t.id"
        >
          {{ t.label }}
          <span v-if="t.id === 'today' && pendingCount" class="badge" :aria-label="`${pendingCount} waiting`">{{ pendingCount }}</span>
        </button>
      </nav>

      <div :id="`pane-${tab}`" ref="pane" class="pane" role="tabpanel" :aria-labelledby="`tab-${tab}`">
        <TeacherToday v-if="tab === 'today'" @teach="teachThis" />
        <TeacherAdd v-else-if="tab === 'add'" @go="(t) => (tab = t)" />
        <TeacherExcel v-else-if="tab === 'excel'" @go="(t) => (tab = t)" />
        <TeacherTeach v-else-if="tab === 'teach'" />
        <TeacherLibrary v-else-if="tab === 'library'" />
        <TeacherLook v-else-if="tab === 'look'" />
        <TeacherAI v-else-if="tab === 'ai'" />
        <TeacherVoice v-else />
      </div>
    </template>

    <p v-if="toast.text" class="toast" :class="{ bad: toast.bad }" role="status">{{ toast.text }}</p>
  </div>
</template>

<style scoped>
.tp { position: fixed; inset: 0; z-index: 40; background: var(--paper); display: flex; flex-direction: column; overflow: hidden; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .8rem 1.4rem; flex-wrap: wrap; }
.bar h2 { font-size: 1.9rem; }
.bar-btns { display: flex; gap: .7rem; flex-wrap: wrap; }

.login-wrap { flex: 1; display: grid; place-items: center; padding: 1rem; overflow-y: auto; }
.login {
  width: min(26rem, 100%); background: #fff; border: 4px solid var(--ink); border-radius: 28px; box-shadow: 0 8px 0 var(--ink);
  padding: 1.6rem; display: flex; flex-direction: column; gap: .8rem;
}
.login h3 { font-size: 1.8rem; }

.tabs { display: flex; gap: .6rem; padding: .2rem 1.4rem .9rem; overflow-x: auto; border-bottom: 3px solid var(--ink); flex: none; }
@media (min-width: 760px) { .tabs { flex-wrap: wrap; overflow-x: visible; padding-bottom: 1rem; } }   /* all the tabs stay in view on a laptop */
.tab {
  flex: none; padding: .5rem 1.1rem; background: #fff; border: 3px solid var(--ink); border-radius: 999px; cursor: pointer;
  font-family: var(--display); font-weight: 700; font-size: 1rem; display: inline-flex; align-items: center; gap: .5rem;
}
.tab.on { background: var(--pink); box-shadow: 0 4px 0 var(--ink); }
.badge { background: var(--berry); color: #fff; border-radius: 999px; min-width: 1.5rem; padding: 0 .45rem; font-size: .85rem; line-height: 1.5rem; text-align: center; }

.pane { flex: 1; min-height: 0; overflow-y: auto; padding: 1.4rem; }

.toast {
  position: fixed; left: 50%; bottom: 1.2rem; transform: translateX(-50%); z-index: 50; max-width: min(36rem, 92vw);
  padding: .8rem 1.3rem; background: var(--good-bg); border: 3px solid var(--ink); border-radius: 18px; box-shadow: 0 5px 0 var(--ink); font-weight: 700;
}
.toast.bad { background: #ffd9d9; }
</style>
