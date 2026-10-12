<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../../api'
import { guard, loadOverview, say } from '../../composables/useTeacher'

// The paid AI is optional. Marshie always looks in her own knowledge first and only asks the AI when she is not sure.
const view = ref(null)
const loading = ref(true)
const busy = ref(false)
const testing = ref(false)
const confirming = ref(false)
const showKey = ref(false)
const result = ref(null)                    // { ok, message, reply } from "Test it"

const form = reactive({ preset: 'anthropic', key: '', model: '', baseUrl: '', enabled: true, dailyLimit: 300 })

const presets = computed(() => view.value?.presets || [])
const preset = computed(() => presets.value.find((p) => p.id === form.preset) || presets.value[0] || {})
const provider = computed(() => preset.value.provider || 'anthropic')
const isLocal = computed(() => /^https?:\/\/(localhost|127\.|10\.|192\.168\.|\[::1\])/i.test(form.baseUrl.trim()))
const needsKey = computed(() => provider.value === 'anthropic' || !isLocal.value)
const sameService = computed(() => {
  const v = view.value
  return !!(v?.saved && v.has_key && v.provider === provider.value && (v.base_url || '') === form.baseUrl.trim().replace(/\/+$/, ''))
})
const canSave = computed(() => !busy.value && (form.key.trim().length >= 8 || sameService.value || !needsKey.value))

function guessPreset(v) {
  if (!v || !v.saved && v.source !== 'env') return 'anthropic'
  if (v.provider === 'anthropic') return 'anthropic'
  const hit = presets.value.find((p) => p.provider === 'openai' && p.base_url && p.base_url.replace(/\/+$/, '') === (v.base_url || '').replace(/\/+$/, ''))
  return hit ? hit.id : 'custom'
}

function fill(v) {
  view.value = v
  form.preset = guessPreset(v)
  form.baseUrl = v.base_url || preset.value.base_url || ''
  form.model = v.model_saved || ''
  form.enabled = v.paused ? false : true
  form.dailyLimit = v.daily_limit || 300
  form.key = ''
  result.value = null
}

async function load() {
  loading.value = true
  const v = await guard(() => api.ai())
  loading.value = false
  if (v) fill(v)
}
onMounted(load)

function choose() {
  // Another service means another address, another model name, and a new key (a key only works for the service that made it).
  form.baseUrl = preset.value.base_url || ''
  form.model = preset.value.model || ''
  form.key = ''
  result.value = null
}

const body = () => ({
  provider: provider.value, key: form.key.trim(), model: form.model.trim(), base_url: form.baseUrl.trim(),
  enabled: form.enabled, daily_limit: Math.min(5000, Math.max(10, Number(form.dailyLimit) || 300)),
})

async function testIt() {
  testing.value = true
  result.value = null
  try {
    result.value = await api.testAi(body())
  } catch (e) {
    if (e.status === 401) await guard(() => { throw e })
    else result.value = { ok: false, message: e.message }
  } finally {
    testing.value = false
  }
}

async function save() {
  busy.value = true
  const v = await guard(() => api.saveAi(body()))
  busy.value = false
  if (!v) return
  fill(v)
  await loadOverview()
  say(v.enabled ? 'Saved. Marshie will ask the AI when she is not sure.' : 'Saved. The AI is paused.')
}

async function remove() {
  if (!confirming.value) { confirming.value = true; setTimeout(() => (confirming.value = false), 5000); return }
  confirming.value = false
  const v = await guard(() => api.removeAi())
  if (!v) return
  fill(v)
  await loadOverview()
  say('The key was removed. Marshie uses only what she has learned.')
}
</script>

<template>
  <div class="tp-section">
    <h3>Paid AI (optional)</h3>
    <p v-if="loading" class="hint">Loading…</p>

    <template v-else-if="view">
      <div class="tp-block">
        <h4>How it works</h4>
        <p>
          Marshie always looks in what she has learned first. Only when she is <b>not sure</b>, she asks the AI service you add here,
          then answers in her own kind, simple words. Everything else stays free and works without the internet.
        </p>
        <p v-if="view.enabled" class="tp-note good" role="status">
          <b>On.</b> Using {{ view.provider === 'anthropic' ? 'Claude' : 'an OpenAI-style service' }} ({{ view.model }}).
          Answered by the AI today: <b>{{ view.used_today }}</b> of {{ view.daily_limit }}.
          <template v-if="view.source === 'env'"> It was set up in this computer’s <code>.env</code> file. Saving here replaces that.</template>
        </p>
        <p v-else-if="view.paused" class="tp-note" role="status"><b>Paused.</b> The key is saved, but Marshie is not using it.</p>
        <p v-else class="tp-note" role="status"><b>Off.</b> Marshie answers only from what she has learned. This is free.</p>
      </div>

      <form class="tp-block" autocomplete="off" @submit.prevent="save">
        <h4>{{ view.saved ? 'Change the AI service' : 'Add an AI service' }}</h4>

        <label class="lbl" for="ai-preset">Which service?</label>
        <select id="ai-preset" v-model="form.preset" class="field" @change="choose">
          <option v-for="p in presets" :key="p.id" :value="p.id">{{ p.label }}</option>
        </select>
        <p v-if="preset.where" class="hint">Make a key on <b>{{ preset.where }}</b>. Most services ask you to add a little credit first.</p>

        <template v-if="needsKey">
          <label class="lbl" for="ai-key">API key</label>
          <div class="keyrow">
            <input id="ai-key" v-model="form.key" class="field" :type="showKey ? 'text' : 'password'" autocomplete="off" spellcheck="false"
                   autocapitalize="off" maxlength="400" :placeholder="sameService ? `Saved key ending ${view.key_hint}. Leave empty to keep it.` : (preset.key_example || 'Paste the key here')" />
            <button type="button" class="btn small white tp-fit" :aria-pressed="showKey" @click="showKey = !showKey">{{ showKey ? 'Hide' : 'Show' }}</button>
          </div>
          <p class="hint">
            The key is kept on the computer that runs Marshie. It is never shown again, never sent to children’s screens and never put in backups.
            <template v-if="view.on_vercel"> Online, it is kept in your Upstash store. For extra safety you can set <code>LLM_PROVIDER</code> and <code>LLM_API_KEY</code> in the Vercel settings instead.</template>
          </p>
        </template>
        <p v-else class="tp-note good">This service runs on this computer or this network, so it needs no key.</p>

        <div v-if="provider === 'openai'">
          <label class="lbl" for="ai-url">Web address of the service</label>
          <input id="ai-url" v-model.trim="form.baseUrl" class="field" type="url" inputmode="url" autocomplete="off" spellcheck="false"
                 placeholder="https://api.example.com/v1" maxlength="300" />
        </div>

        <div class="tp-row">
          <div>
            <label class="lbl" for="ai-model">Model name (optional)</label>
            <input id="ai-model" v-model.trim="form.model" class="field" type="text" autocomplete="off" spellcheck="false" maxlength="100"
                   :placeholder="preset.model || view.model_default || 'Copy it from the service’s website'" />
          </div>
          <div class="tp-fit">
            <label class="lbl" for="ai-limit">Most AI answers each day</label>
            <input id="ai-limit" v-model.number="form.dailyLimit" class="field" type="number" min="10" max="5000" step="10" style="width: 9rem" />
          </div>
        </div>
        <p class="hint">
          You pay the service for every answer it gives, a very small amount each. The daily limit protects you from a surprise bill:
          after that many, Marshie goes back to what she has learned until tomorrow. Leaving the model empty uses a small, cheap one.
        </p>

        <label class="tp-check">
          <input v-model="form.enabled" type="checkbox" />
          <span><b>Use the AI</b><br /><span class="hint">Switch this off to pause it without losing the key.</span></span>
        </label>

        <div class="tp-row actions">
          <button type="button" class="btn white tp-fit" :disabled="testing || !canSave" @click="testIt">{{ testing ? 'Trying…' : 'Test it' }}</button>
          <button type="submit" class="btn green tp-fit" :disabled="!canSave">{{ busy ? 'Saving…' : 'Save' }}</button>
          <button v-if="view.saved" type="button" class="btn small tp-fit" :class="confirming ? 'berry' : 'white'" @click="remove">
            {{ confirming ? 'Press again to remove the key' : 'Remove the key' }}
          </button>
        </div>

        <p v-if="result" class="tp-note" :class="result.ok ? 'good' : 'bad'" :role="result.ok ? 'status' : 'alert'">
          {{ result.message }}<template v-if="result.reply"> It said: “{{ result.reply }}”</template>
        </p>
      </form>

      <div class="tp-note">
        <b>Please tell parents and teachers.</b> When Marshie asks the AI, the child’s question and a few lines of the school’s own facts are sent to the service.
        Ask the children not to type their full names, addresses or phone numbers. Marshie also refuses rude questions before they get that far.
      </div>
    </template>
  </div>
</template>

<style scoped>
.keyrow { display: flex; gap: .6rem; align-items: center; }
.keyrow .field { flex: 1 1 auto; min-width: 0; font-family: ui-monospace, Menlo, Consolas, monospace; }
form.tp-block { display: flex; flex-direction: column; gap: .5rem; }
.actions { margin-top: .4rem; }
select.field { appearance: auto; }
</style>
