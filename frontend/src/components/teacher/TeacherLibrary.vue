<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { authed, guard, loadOverview, overview, say, when } from '../../composables/useTeacher'

const PAGE = 25
const q = ref('')
const via = ref('')
const category = ref('')
const offset = ref(0)
const list = ref({ total: 0, entries: [] })
const loading = ref(false)
const confirming = ref('')
const confirmingTable = ref('')
const confirmingFile = ref('')
const files = ref([])

const VIA = { seed: 'Built in', teach: 'Taught', excel: 'Excel', media: 'Picture or sound', document: 'Document', import: 'Restored' }
const categories = computed(() => Object.keys(overview.value?.stats?.categories || {}))
const tables = computed(() => overview.value?.datasets || [])
const pages = computed(() => Math.max(1, Math.ceil(list.value.total / PAGE)))
const page = computed(() => Math.floor(offset.value / PAGE) + 1)

async function load() {
  loading.value = true
  const params = { limit: String(PAGE), offset: String(offset.value) }
  if (q.value.trim()) params.q = q.value.trim()
  if (via.value) params.via = via.value
  if (category.value) params.category = category.value
  const res = await guard(() => api.entries(params))
  loading.value = false
  if (res) list.value = res
}

let debounce = null
watch([q], () => { clearTimeout(debounce); debounce = setTimeout(() => { offset.value = 0; load() }, 300) })
watch([via, category], () => { offset.value = 0; load() })
async function loadFiles() {
  const res = await guard(() => api.library())
  if (res) files.value = res.items
}
onMounted(() => { load(); loadFiles(); if (!overview.value) loadOverview() })

function go(step) {
  offset.value = Math.max(0, offset.value + step * PAGE)
  load()
}

async function remove(e) {
  if (confirming.value !== e.id) { confirming.value = e.id; return }
  confirming.value = ''
  if (await guard(() => api.deleteEntry(e.id))) { say('Deleted. Marshie has forgotten it.'); await load(); loadOverview() }
}
async function removeFile(f) {
  if (confirmingFile.value !== f.id) { confirmingFile.value = f.id; return }
  confirmingFile.value = ''
  if (await guard(() => api.deleteLibraryItem(f.id))) { say('Deleted. Marshie has forgotten it.'); await Promise.all([loadFiles(), load()]); loadOverview() }
}
const TYPE = { image: 'Picture', audio: 'Recording', video: 'Video', document: 'Document' }
const size = (f) => (f.type === 'document' ? `${f.entries} passages` : f.size >= 1048576 ? `${(f.size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(f.size / 1024))} KB`)
async function removeTable(t) {
  if (confirmingTable.value !== t.id) { confirmingTable.value = t.id; return }
  confirmingTable.value = ''
  if (await guard(() => api.deleteDataset(t.id))) { say('Table deleted.'); loadOverview() }
}

const xlsxUrl = computed(() => { void authed.value; return api.downloadUrl('/api/admin/export', { format: 'xlsx' }) })
const jsonUrl = computed(() => { void authed.value; return api.downloadUrl('/api/admin/export', { format: 'json' }) })
const zipUrl = computed(() => { void authed.value; return api.downloadUrl('/api/admin/export', { format: 'zip' }) })

async function restore(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) return
  const res = await guard(() => api.restore(f))
  if (res) { say(`Restored ${res.added} things${res.files ? ` and ${res.files} files` : ''} (${res.duplicates} were already known).`); load(); loadFiles(); loadOverview() }
}
</script>

<template>
  <div class="tp-section">
    <h3>What Marshie knows</h3>

    <div class="tp-block">
      <div class="tp-row">
        <div>
          <label class="lbl" for="l-q">Search</label>
          <input id="l-q" v-model="q" class="field" type="search" placeholder="A word from a question or answer" />
        </div>
        <div>
          <label class="lbl" for="l-v">Where it came from</label>
          <select id="l-v" v-model="via" class="field">
            <option value="">Everything</option>
            <option v-for="(label, key) in VIA" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
        <div>
          <label class="lbl" for="l-c">Subject</label>
          <select id="l-c" v-model="category" class="field">
            <option value="">All subjects</option>
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
      </div>

      <p class="hint" aria-live="polite">{{ loading ? 'Looking…' : `${list.total} found` }}</p>
      <ul class="tp-list">
        <li v-for="e in list.entries" :key="e.id" class="tp-item">
          <div class="main">
            <p class="q"><span class="tp-tag">{{ VIA[e.via] || e.via }}</span>{{ e.question }}</p>
            <p class="a">{{ e.answer }}</p>
            <p class="meta">{{ e.category }}<template v-if="e.added_by">, by {{ e.added_by }}</template><template v-if="e.status === 'pending'">, waiting to be approved</template><template v-if="e.via !== 'seed'">, {{ when(e.created) }}</template></p>
          </div>
          <div v-if="e.via !== 'seed'" class="acts">
            <button class="btn small" :class="confirming === e.id ? 'berry' : 'white'" @click="remove(e)">
              {{ confirming === e.id ? 'Yes, delete' : 'Delete' }}
            </button>
          </div>
        </li>
      </ul>
      <div v-if="list.total > PAGE" class="tp-row pager">
        <button class="btn small white" :disabled="page <= 1" @click="go(-1)">Previous</button>
        <span class="hint">Page {{ page }} of {{ pages }}</span>
        <button class="btn small white" :disabled="page >= pages" @click="go(1)">Next</button>
      </div>
    </div>

    <div class="tp-block">
      <h4>Pictures, recordings and documents</h4>
      <p v-if="!files.length" class="hint">None yet. Add some in <b>Add data</b>.</p>
      <ul v-else class="tp-list">
        <li v-for="f in files" :key="f.id" class="tp-item">
          <img v-if="f.type === 'image'" class="thumb" :src="f.url" :alt="f.title" loading="lazy" />
          <div class="main">
            <p class="q"><span class="tp-tag">{{ TYPE[f.type] }}</span>{{ f.title }}</p>
            <p class="meta">{{ size(f) }}<template v-if="f.filename">, {{ f.filename }}</template>, {{ when(f.created) }}</p>
            <audio v-if="f.type === 'audio'" class="player" :src="f.url" controls preload="none"></audio>
          </div>
          <div class="acts">
            <button class="btn small" :class="confirmingFile === f.id ? 'berry' : 'white'" @click="removeFile(f)">
              {{ confirmingFile === f.id ? 'Yes, delete' : 'Delete' }}
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div class="tp-block">
      <h4>Data tables from Excel</h4>
      <p v-if="!tables.length" class="hint">None yet. Upload a sheet with a data table and children can ask things like “What is the average height?”.</p>
      <ul v-else class="tp-list">
        <li v-for="t in tables" :key="t.id" class="tp-item">
          <div class="main">
            <p class="q">{{ t.name }}</p>
            <p class="meta">{{ t.rows }} rows. Columns: {{ t.columns.join(', ') }}</p>
          </div>
          <div class="acts">
            <button class="btn small" :class="confirmingTable === t.id ? 'berry' : 'white'" @click="removeTable(t)">
              {{ confirmingTable === t.id ? 'Yes, delete' : 'Delete' }}
            </button>
          </div>
        </li>
      </ul>
    </div>

    <div class="tp-block">
      <h4>Keep a copy safe</h4>
      <p class="hint">
        Download a backup now and then. You can restore it on another computer, or put the file in the project’s
        <code>backend/app/data/custom</code> folder so it ships with Marshie when you publish her online.
      </p>
      <div class="tp-row">
        <a class="btn white tp-fit" :href="zipUrl" download>Download everything with pictures and sound (.zip)</a>
        <a class="btn white tp-fit" :href="jsonUrl" download>Download the words only (.json)</a>
        <a class="btn white tp-fit" :href="xlsxUrl" download>Download what she learned (Excel)</a>
        <label class="btn white tp-fit">
          Restore a backup
          <input type="file" accept=".json,.zip,application/json,application/zip" class="sr-only" @change="restore" />
        </label>
      </div>
    </div>
  </div>
</template>

<style scoped>
.thumb { width: 4.6rem; height: 4.6rem; object-fit: cover; border: 2px solid var(--ink); border-radius: 12px; background: #fff; flex: none; }
.player { margin-top: .4rem; width: min(100%, 18rem); }
.pager { align-items: center; justify-content: center; }
.pager > * { flex: none; }
label.btn:focus-within { outline: 4px solid var(--ink); outline-offset: 3px; }
</style>
