<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { api } from '../../api'
import { guard, loadOverview, overview, say } from '../../composables/useTeacher'
import { transcribeFile } from '../../composables/useTranscribe'
import { fitImage } from '../../composables/fitImage'
import ExcelPreview from './ExcelPreview.vue'

defineEmits(['go'])

const EXT = {
  image: ['png', 'jpg', 'jpeg', 'gif', 'webp'],
  audio: ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'oga', 'opus', 'flac', 'webm'],
  video: ['mp4', 'm4v', 'mov', 'webm'],
  document: ['pdf', 'docx', 'pptx', 'txt', 'md', 'html', 'htm', 'rtf'],
  sheet: ['xlsx', 'xlsm', 'csv'],
  backup: ['json', 'zip'],
}
const ACCEPT = Object.values(EXT).flat().map((e) => '.' + e).join(',')
const LABEL = { image: 'Picture', audio: 'Recording', video: 'Video', document: 'Document', sheet: 'Excel sheet', backup: 'Backup' }

const features = computed(() => overview.value?.features || {})
const limitBytes = computed(() => Math.floor((features.value.media_mb || 3) * 1024 * 1024))

function kindOf(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (EXT.sheet.includes(ext)) return 'sheet'
  if (EXT.document.includes(ext)) return 'document'
  if (EXT.backup.includes(ext)) return 'backup'
  if (EXT.image.includes(ext)) return 'image'
  if ((ext === 'webm' || ext === 'ogg') && file.type.startsWith('video/')) return 'video'
  if (EXT.audio.includes(ext)) return 'audio'
  if (EXT.video.includes(ext)) return 'video'
  return ''
}
const stem = (name) => name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim()

// ------------------------------------------------------------------ the list of files being added
const items = ref([])
const over = ref(false)
let nextId = 1

function newItem(file) {
  const kind = kindOf(file)
  return reactive({
    id: nextId++, file, kind, status: 'ready', busy: false, error: '', url: '', preview: null, result: null,
    title: stem(file.name), say: '', questions: '', category: '', transcript: '', progress: -1,
  })
}

async function run(item, fn) {
  item.busy = true
  item.error = ''
  try {
    return await fn()
  } catch (e) {
    if (e.status === 401) await guard(async () => { throw e })
    else item.error = e.message
    return undefined
  } finally {
    item.busy = false
  }
}

async function addFiles(list) {
  if (!overview.value) await loadOverview()        // the size limit comes from there
  for (const f of Array.from(list || [])) {
    const item = newItem(f)
    items.value.push(item)
    if (!item.kind) {
      item.status = 'error'
      item.error = `I can’t use .${f.name.split('.').pop()} files. Try a picture, recording, video, document or Excel sheet.`
      continue
    }
    if (item.kind === 'image') {
      item.file = await fitImage(f, limitBytes.value)
      item.url = URL.createObjectURL(item.file)
    } else if (item.kind === 'audio' || item.kind === 'video') {
      item.url = URL.createObjectURL(f)
    }
    if ((item.kind === 'image' || item.kind === 'audio' || item.kind === 'video') && item.file.size > limitBytes.value) {
      item.status = 'error'
      item.error = `That file is ${(item.file.size / 1048576).toFixed(1)} MB. The limit here is ${(limitBytes.value / 1048576).toFixed(0)} MB. Make it smaller, or run Marshie on a computer for bigger files.`
    } else if (item.kind === 'document') {
      await previewDocument(item)
    } else if (item.kind === 'sheet') {
      const res = await run(item, () => api.upload(item.file, false))
      if (res) item.preview = res
      else item.status = 'error'
    }
  }
}

async function previewDocument(item) {
  const form = new FormData()
  form.append('file', item.file)
  const res = await run(item, () => api.addDocument(form))
  if (res) { item.preview = res; item.title = res.title } else item.status = 'error'
}

function remove(item) {
  if (item.url) URL.revokeObjectURL(item.url)
  items.value = items.value.filter((i) => i !== item)
}
onBeforeUnmount(() => items.value.forEach((i) => i.url && URL.revokeObjectURL(i.url)))

const onInput = (e) => { addFiles(e.target.files); e.target.value = '' }
const onDrop = (e) => { over.value = false; addFiles(e.dataTransfer?.files) }

// ------------------------------------------------------------------ keeping them
async function commit(item) {
  if (item.busy) return
  let res
  if (item.kind === 'image' || item.kind === 'audio' || item.kind === 'video') {
    const form = new FormData()
    form.append('file', item.file)
    form.append('title', item.title)
    form.append('say', item.say)
    form.append('questions', item.questions)
    form.append('category', item.category)
    form.append('transcript', item.transcript)
    res = await run(item, () => api.addMedia(form))
    if (res) item.result = `Done. Try asking Marshie: “${item.kind === 'audio' ? 'Play' : 'Show me'} ${res.title}”.`
  } else if (item.kind === 'document') {
    const form = new FormData()
    form.append('file', item.file)
    form.append('title', item.title)
    form.append('category', item.category)
    form.append('commit', 'true')
    res = await run(item, () => api.addDocument(form))
    if (res) item.result = `Done. Marshie learned ${res.added} ${res.added === 1 ? 'passage' : 'passages'} from it. Ask her something that is in the document.`
  } else if (item.kind === 'sheet') {
    res = await run(item, () => api.upload(item.file, true))
    if (res) {
      item.result = `Done. Marshie learned ${res.added} new ${res.added === 1 ? 'thing' : 'things'}`
        + (res.datasets_added ? ` and ${res.datasets_added} data ${res.datasets_added === 1 ? 'table' : 'tables'}` : '')
        + (res.duplicates ? `. ${res.duplicates} ${res.duplicates === 1 ? 'was' : 'were'} already known` : '') + '.'
    }
  } else if (item.kind === 'backup') {
    res = await run(item, () => api.restore(item.file))
    if (res) item.result = `Restored ${res.added} things${res.files ? ` and ${res.files} files` : ''} (${res.duplicates} were already known).`
  }
  if (res) {
    item.status = 'done'
    item.preview = null
    say('Added. Marshie knows it now.')
    loadOverview()
  }
}

const readyItems = computed(() => items.value.filter((i) => i.status === 'ready' && !i.busy && canAdd(i)))
function canAdd(item) {
  if (item.kind === 'sheet') return !!item.preview && (item.preview.to_add || item.preview.datasets.length)
  if (item.kind === 'document') return !!item.preview
  if (item.kind === 'backup') return true
  return item.title.trim().length > 0
}
async function addAll() { for (const i of [...readyItems.value]) await commit(i) }

// ------------------------------------------------------------------ writing out a recording
const canTranscribe = computed(() => !!features.value.transcribe)
async function transcribe(item) {
  item.progress = 0
  const text = await run(item, () => transcribeFile(item.file, (p) => { item.progress = p }))
  item.progress = -1
  if (text === undefined) return
  if (!text) item.error = 'I could not hear any words in that recording. You can type what it says instead.'
  else item.transcript = text
}

// ------------------------------------------------------------------ recording a voice note
const canRecord = typeof window !== 'undefined' && typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && window.isSecureContext
const recording = ref(false)
const seconds = ref(0)
let recorder = null
let stream = null
let tick = null

async function toggleRecord() {
  if (recording.value) { recorder?.stop(); return }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch {
    say('I need to use the microphone to record. Please allow it and try again.', true)
    return
  }
  const chunks = []
  const mime = ['audio/webm', 'audio/mp4', 'audio/ogg'].find((m) => MediaRecorder.isTypeSupported(m))
  recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
  recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
  recorder.onstop = () => {
    stream.getTracks().forEach((t) => t.stop())
    clearInterval(tick)
    recording.value = false
    const type = (recorder.mimeType || 'audio/webm').split(';')[0]
    const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm'
    const when = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }).replace(':', '.')
    addFiles([new File(chunks, `Recording ${when}.${ext}`, { type })])
  }
  seconds.value = 0
  recording.value = true
  recorder.start()
  tick = setInterval(() => { seconds.value += 1; if (seconds.value >= 300) recorder?.stop() }, 1000)
}
onBeforeUnmount(() => { clearInterval(tick); if (recording.value) recorder?.stop() })

// ------------------------------------------------------------------ pasted text
const pasteTitle = ref('')
const pasteText = ref('')
const pasteCategory = ref('')
const pasteBusy = ref(false)
const pasteDone = ref('')
async function addPasted() {
  pasteBusy.value = true
  pasteDone.value = ''
  const form = new FormData()
  form.append('text', pasteText.value)
  form.append('title', pasteTitle.value)
  form.append('category', pasteCategory.value)
  form.append('commit', 'true')
  const res = await guard(() => api.addDocument(form))
  pasteBusy.value = false
  if (res) {
    pasteDone.value = `Done. Marshie learned ${res.added} ${res.added === 1 ? 'passage' : 'passages'}.`
    pasteText.value = ''
    pasteTitle.value = ''
    loadOverview()
  }
}
const size = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)
const mm = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
</script>

<template>
  <div class="tp-section">
    <h3>Add anything for Marshie to learn</h3>

    <div class="tp-block">
      <label class="tp-drop" :class="{ over }" @dragover.prevent="over = true" @dragleave="over = false" @drop.prevent="onDrop">
        <input type="file" multiple :accept="ACCEPT" @change="onInput" />
        <b>Choose files, or drop them here</b><br />
        <span class="hint">Excel sheets, pictures, recordings, videos, PDF, Word and PowerPoint files, or plain text. I will show you each one before it is added.</span>
      </label>
      <div class="tp-row tools">
        <button v-if="canRecord" type="button" class="btn white tp-fit" :class="{ rec: recording }" @click="toggleRecord">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="6" /></svg>
          {{ recording ? `Stop recording (${mm(seconds)})` : 'Record my voice' }}
        </button>
        <button type="button" class="btn white tp-fit" @click="$emit('go', 'excel')">Make an Excel sheet to fill in</button>
      </div>
      <p class="hint">
        Pictures and recordings can be up to {{ features.media_mb || 3 }} MB here. Big photos are shrunk for you.
        <template v-if="overview?.on_vercel">Online, files are kept in your Upstash store, so keep them small.</template>
      </p>
    </div>

    <ul v-if="items.length" class="queue tp-list">
      <li v-for="item in items" :key="item.id" class="tp-block card" :class="{ done: item.status === 'done', bad: item.status === 'error' }">
        <div class="head">
          <span class="tp-tag">{{ LABEL[item.kind] || 'File' }}</span>
          <b class="fname">{{ item.file.name }}</b>
          <span class="hint">{{ size(item.file.size) }}</span>
          <button type="button" class="btn small white tp-fit" :disabled="item.busy" @click="remove(item)">{{ item.status === 'done' ? 'Clear' : 'Remove' }}</button>
        </div>

        <p v-if="item.error" class="tp-note bad" role="alert">{{ item.error }}</p>
        <p v-if="item.result" class="tp-note good" role="status">{{ item.result }}</p>

        <template v-if="item.status === 'ready'">
          <!-- pictures, recordings and videos -->
          <div v-if="['image', 'audio', 'video'].includes(item.kind)" class="media-form">
            <div class="thumb">
              <img v-if="item.kind === 'image'" :src="item.url" :alt="`Preview of ${item.title}`" />
              <video v-else-if="item.kind === 'video'" :src="item.url" controls preload="metadata"></video>
              <audio v-else :src="item.url" controls preload="metadata"></audio>
            </div>
            <div class="fields">
              <div>
                <label class="lbl" :for="`t-${item.id}`">Name (children ask for it by this name)</label>
                <input :id="`t-${item.id}`" v-model="item.title" class="field" type="text" maxlength="100" />
              </div>
              <div>
                <label class="lbl" :for="`s-${item.id}`">What Marshie says (optional)</label>
                <input :id="`s-${item.id}`" v-model="item.say" class="field" type="text" maxlength="600"
                       :placeholder="item.kind === 'audio' ? `Listen! Press play to hear ${item.title}.` : `Here it is: ${item.title}!`" />
              </div>
              <div>
                <label class="lbl" :for="`q-${item.id}`">Other ways children might ask (optional, one on each line)</label>
                <textarea :id="`q-${item.id}`" v-model="item.questions" class="field" rows="2" placeholder="What does our school gate look like?"></textarea>
              </div>
              <div v-if="item.kind === 'audio'">
                <label class="lbl" :for="`x-${item.id}`">What the recording says (optional)</label>
                <textarea :id="`x-${item.id}`" v-model="item.transcript" class="field" rows="3"
                          placeholder="Type or paste the words. Then children can ask about what is said in it."></textarea>
                <div class="tp-row">
                  <button v-if="canTranscribe" type="button" class="btn small white tp-fit" :disabled="item.busy" @click="transcribe(item)">
                    {{ item.progress >= 0 ? `Listening… ${Math.round(item.progress * 100)}%` : 'Write it out for me' }}
                  </button>
                  <span v-else class="hint">To have Marshie write recordings out for you, install the offline listener: <code>python marshie.py voice</code>.</span>
                </div>
              </div>
            </div>
          </div>

          <!-- documents -->
          <div v-else-if="item.kind === 'document'" class="doc-form">
            <p v-if="item.busy && !item.preview" class="hint">Reading the document…</p>
            <template v-if="item.preview">
              <p>
                Found <b>{{ item.preview.passages }}</b> {{ item.preview.passages === 1 ? 'passage' : 'passages' }}
                ({{ item.preview.characters.toLocaleString() }} letters). Marshie will find the right passage when someone asks.
                <template v-if="item.preview.replaces"><b>This replaces the earlier copy of the same file.</b></template>
              </p>
              <div class="tp-scroll">
                <table class="tp-table">
                  <thead><tr><th>A few of the passages</th></tr></thead>
                  <tbody><tr v-for="(p, i) in item.preview.sample" :key="i"><td>{{ p }}</td></tr></tbody>
                </table>
              </div>
              <div class="tp-row">
                <div>
                  <label class="lbl" :for="`dt-${item.id}`">Name of the document</label>
                  <input :id="`dt-${item.id}`" v-model="item.title" class="field" type="text" maxlength="120" />
                </div>
                <div>
                  <label class="lbl" :for="`dc-${item.id}`">Subject (optional)</label>
                  <input :id="`dc-${item.id}`" v-model="item.category" class="field" type="text" maxlength="60" placeholder="Documents" />
                </div>
              </div>
            </template>
          </div>

          <!-- Excel sheets -->
          <div v-else-if="item.kind === 'sheet'">
            <p v-if="item.busy && !item.preview" class="hint">Reading the sheet…</p>
            <ExcelPreview v-if="item.preview" :preview="item.preview" />
          </div>

          <!-- backups -->
          <p v-else-if="item.kind === 'backup'" class="hint">
            This looks like a Marshie backup. Adding it restores what is inside (things that Marshie already knows are skipped).
          </p>

          <div v-if="item.kind" class="go">
            <button type="button" class="btn green" :disabled="item.busy || !canAdd(item)" @click="commit(item)">
              {{ item.busy ? 'Adding…' : item.kind === 'backup' ? 'Restore this backup' : 'Add to Marshie' }}
            </button>
          </div>
        </template>
      </li>
    </ul>

    <div v-if="readyItems.length > 1" class="tp-row">
      <button type="button" class="btn green tp-fit" @click="addAll">Add all {{ readyItems.length }} to Marshie</button>
    </div>

    <div class="tp-block">
      <h4>Or paste some text</h4>
      <p class="hint">A page from a textbook, school notes, a story. Marshie cuts it into short passages and reads the right one out.</p>
      <div class="tp-row">
        <div>
          <label class="lbl" for="pt-title">Name</label>
          <input id="pt-title" v-model="pasteTitle" class="field" type="text" maxlength="120" placeholder="Our school garden" />
        </div>
        <div>
          <label class="lbl" for="pt-cat">Subject (optional)</label>
          <input id="pt-cat" v-model="pasteCategory" class="field" type="text" maxlength="60" placeholder="Science" />
        </div>
      </div>
      <label class="lbl" for="pt-text">The text</label>
      <textarea id="pt-text" v-model="pasteText" class="field" rows="5" placeholder="Paste or type here…"></textarea>
      <div class="tp-row">
        <button type="button" class="btn green tp-fit" :disabled="pasteBusy || pasteText.trim().length < 25" @click="addPasted">
          {{ pasteBusy ? 'Adding…' : 'Add this text to Marshie' }}
        </button>
      </div>
      <p v-if="pasteDone" class="tp-note good" role="status">{{ pasteDone }}</p>
    </div>
  </div>
</template>

<style scoped>
.tools { align-items: center; }
.rec { background: var(--berry); color: #fff; }
.rec svg { animation: blinkRec 1s steps(2) infinite; }
@keyframes blinkRec { 50% { opacity: .2 } }
.queue { gap: 1rem; }
.card { gap: .9rem; }
.card.done { background: var(--good-bg); }
.head { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.head .fname { flex: 1; min-width: 8rem; overflow-wrap: anywhere; }
.media-form { display: grid; grid-template-columns: minmax(8rem, 14rem) 1fr; gap: 1.1rem; align-items: start; }
.thumb img { width: 100%; max-height: 14rem; object-fit: contain; border: 3px solid var(--ink); border-radius: 16px; background: #fff; display: block; }
.thumb video { width: 100%; border-radius: 12px; background: #000; }
.thumb audio { width: 100%; }
.fields { display: flex; flex-direction: column; gap: .7rem; min-width: 0; }
.doc-form { display: flex; flex-direction: column; gap: .8rem; }
.go { display: flex; }
@media (max-width: 700px) { .media-form { grid-template-columns: 1fr; } }
</style>
