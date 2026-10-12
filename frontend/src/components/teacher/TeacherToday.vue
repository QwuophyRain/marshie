<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../../api'
import { guard, loadOverview, overview, say, when } from '../../composables/useTeacher'

defineEmits(['teach'])

const pending = ref([])
const ov = computed(() => overview.value)
const stats = computed(() => ov.value?.stats)
const moderate = computed(() => !!ov.value?.settings?.moderate_teaching)

async function refresh() {
  await loadOverview()
  const res = await guard(() => api.entries({ status: 'pending', limit: 100 }))
  pending.value = res?.entries || []
}
onMounted(refresh)

async function toggleModeration(e) {
  const on = e.target.checked
  const res = await guard(() => api.setSettings({ moderate_teaching: on }))
  if (res) say(on ? 'Okay. I will wait for you to approve what children teach me.' : 'Okay. I will learn what children teach me straight away.')
  await loadOverview()
}

async function approve(entry) {
  if (await guard(() => api.approveEntry(entry.id))) { say('Approved. Marshie knows it now.'); await refresh() }
}
async function remove(entry) {
  if (await guard(() => api.deleteEntry(entry.id))) { say('Deleted.'); await refresh() }
}

// Undo takes back everything one upload added. It asks twice, because it cannot itself be undone.
const sure = ref('')
async function undo(u) {
  if (sure.value !== u.id) { sure.value = u.id; setTimeout(() => { if (sure.value === u.id) sure.value = '' }, 5000); return }
  sure.value = ''
  const res = await guard(() => api.undoUpload(u.id))
  if (!res) return
  const parts = []
  if (res.facts) parts.push(`${res.facts} ${res.facts === 1 ? 'thing' : 'things'}`)
  if (res.tables) parts.push(`${res.tables} data ${res.tables === 1 ? 'table' : 'tables'}`)
  if (res.files) parts.push(`${res.files === 1 ? 'the file' : res.files + ' files'}`)
  say(`Undone. Marshie has forgotten ${parts.join(' and ') || 'it'}.`)
  await refresh()
}
</script>

<template>
  <div v-if="!ov" class="tp-section"><p>Loading…</p></div>
  <div v-else class="tp-section">
    <div v-if="ov.default_pin" class="tp-note bad">
      The teacher PIN is still the starting one (2468). Open the <code>.env</code> file, change <code>ADMIN_PIN</code>, then restart Marshie.
    </div>
    <div v-if="ov.on_vercel && !stats.persistent" class="tp-note bad">
      This online copy forgets what it learns after a while, because no storage is connected. Add a Vercel KV or Upstash Redis store,
      or download a backup from “What Marshie knows” and keep it safe.
    </div>

    <div v-if="stats.state_limit_kb && stats.state_kb > stats.state_limit_kb * 0.8" class="tp-note bad">
      Marshie’s online memory is nearly full ({{ stats.state_kb }} KB of about {{ stats.state_limit_kb }} KB). Delete documents or tables she does not need,
      or run her on a computer where there is no such limit.
    </div>

    <div class="tp-grid">
      <div class="tp-stat"><b>{{ stats.total_entries }}</b><span>things Marshie knows</span></div>
      <div class="tp-stat"><b>{{ stats.learned }}</b><span>taught by you and the students</span></div>
      <div class="tp-stat"><b>{{ stats.pending }}</b><span>waiting for you to check</span></div>
      <div class="tp-stat"><b>{{ stats.datasets }}</b><span>data tables ({{ stats.dataset_rows }} rows)</span></div>
      <div class="tp-stat"><b>{{ stats.media + stats.documents }}</b><span>pictures, recordings and documents</span></div>
      <div class="tp-stat"><b>{{ stats.ratings_good }} / {{ stats.ratings_bad }}</b><span>marked right / wrong</span></div>
    </div>

    <div class="tp-block">
      <h4>Teaching rules</h4>
      <label class="tp-check">
        <input type="checkbox" :checked="moderate" @change="toggleModeration" />
        <span>
          <b>Check answers before Marshie learns them.</b><br />
          <span class="hint">When this is on, anything a child teaches in the chat waits here for your OK. Excel sheets, pictures, recordings and documents you add are always added straight away.</span>
        </span>
      </label>
    </div>

    <div v-if="pending.length" class="tp-block">
      <h4>Waiting for you to check ({{ pending.length }})</h4>
      <ul class="tp-list">
        <li v-for="e in pending" :key="e.id" class="tp-item">
          <div class="main">
            <p class="q">{{ e.question }}</p>
            <p class="a">{{ e.answer }}</p>
            <p class="meta">Taught by {{ e.added_by || 'a student' }} on {{ when(e.created) }}</p>
          </div>
          <div class="acts">
            <button class="btn small green" @click="approve(e)">Approve</button>
            <button class="btn small berry" @click="remove(e)">Delete</button>
          </div>
        </li>
      </ul>
    </div>

    <div class="tp-block">
      <h4>Questions Marshie could not answer</h4>
      <p v-if="!ov.unknown.length" class="hint">Nothing yet. When someone asks something Marshie does not know, it appears here so you can teach her.</p>
      <ul v-else class="tp-list">
        <li v-for="u in ov.unknown" :key="u.q" class="tp-item">
          <div class="main">
            <p class="q">{{ u.q }}</p>
            <p class="meta">Asked {{ u.n }} {{ u.n === 1 ? 'time' : 'times' }}, last on {{ when(u.ts) }}</p>
          </div>
          <div class="acts"><button class="btn small pink" @click="$emit('teach', u.q)">Teach the answer</button></div>
        </li>
      </ul>
    </div>

    <div class="tp-block">
      <h4>How Marshie is set up</h4>
      <ul class="tp-list">
        <li class="tp-item"><span class="main">
          <b>Thinking:</b>
          {{ ov.llm.enabled ? `Using an AI service (${ov.llm.provider}, ${ov.llm.model}) when her own knowledge is not enough.` : 'Using only what she has learned. No AI key is needed. You can add one later in the Paid AI tab.' }}
        </span></li>
        <li class="tp-item"><span class="main">
          <b>Talking:</b>
          {{ ov.voice.tts_server ? 'Using the offline voice on this computer.' : 'Using the voice built into the browser.' }}
        </span></li>
        <li class="tp-item"><span class="main">
          <b>Listening:</b>
          {{ ov.voice.stt_server ? 'Using the offline listener on this computer.' : 'Using the browser’s speech recognition (works in Chrome and Edge, needs the internet).' }}
        </span></li>
        <li class="tp-item"><span class="main">
          <b>Memory:</b>
          {{ stats.storage === 'kv' ? 'Saved in online storage.' : stats.storage === 'tmp' ? 'Temporary. It is lost when the online copy restarts.' : 'Saved on this computer in the data folder.' }}
        </span></li>
      </ul>
    </div>

    <div v-if="ov.uploads.length" class="tp-block">
      <h4>Recent uploads</h4>
      <ul class="tp-list">
        <li v-for="u in ov.uploads" :key="u.id || u.ts + u.filename" class="tp-item">
          <span class="main"><b>{{ u.filename }}</b><br />
            <span class="meta">{{ when(u.ts) }}: {{ u.added }} new, {{ u.duplicates }} already known<template v-if="u.datasets">, {{ u.datasets }} data {{ u.datasets === 1 ? 'table' : 'tables' }}</template><template v-if="u.errors">, {{ u.errors }} rows skipped</template><template v-if="u.undone">. Undone</template></span>
          </span>
          <span v-if="u.can_undo" class="acts">
            <button type="button" class="btn small" :class="sure === u.id ? 'berry' : 'white'" @click="undo(u)">
              {{ sure === u.id ? 'Yes, undo it' : 'Undo' }}
            </button>
          </span>
        </li>
      </ul>
      <p class="hint">
        <b>Undo</b> takes back everything that upload added: its facts, tables, pictures and recordings. Anything Marshie already knew before is kept.
        It cannot bring back something the upload replaced (a table or document with the same name).
      </p>
    </div>
  </div>
</template>
