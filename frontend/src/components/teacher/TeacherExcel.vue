<script setup>
import { computed, ref } from 'vue'
import { api } from '../../api'
import { authed } from '../../composables/useTeacher'

defineEmits(['go'])

const kind = ref('all')
const className = ref('')
const category = ref('')
const rows = ref(50)
const datasetName = ref('')
const columns = ref('')

const KINDS = [
  { id: 'all', label: 'All three sheets', hint: 'Questions and answers, facts, and a data table in one file. Students use the sheet that fits.' },
  { id: 'qa', label: 'Questions and answers', hint: 'One question and one answer on each row.' },
  { id: 'facts', label: 'Facts', hint: 'A topic and a fact about it on each row.' },
  { id: 'data', label: 'A data table', hint: 'Numbers the class measured or surveyed, with columns you choose.' },
]
const wantsData = computed(() => kind.value === 'data' || kind.value === 'all')

const templateUrl = computed(() => {
  void authed.value
  const params = { kind: kind.value, rows: String(rows.value || 50) }
  if (className.value.trim()) params.class_name = className.value.trim()
  if (category.value.trim()) params.category = category.value.trim()
  if (wantsData.value && columns.value.trim()) params.columns = columns.value.trim()
  if (wantsData.value && datasetName.value.trim()) params.dataset_name = datasetName.value.trim()
  return api.downloadUrl('/api/admin/template', params)
})
</script>

<template>
  <div class="tp-section">
    <h3>Make an Excel sheet for the students</h3>
    <div class="tp-block">
      <fieldset class="kinds">
        <legend class="lbl">What should the students fill in?</legend>
        <label v-for="k in KINDS" :key="k.id" class="kind" :class="{ on: kind === k.id }">
          <input v-model="kind" type="radio" name="kind" :value="k.id" />
          <span><b>{{ k.label }}</b><br /><span class="hint">{{ k.hint }}</span></span>
        </label>
      </fieldset>

      <div class="tp-row">
        <div>
          <label class="lbl" for="x-class">Class or group (optional)</label>
          <input id="x-class" v-model="className" class="field" type="text" placeholder="JHS 2 Science Club" />
        </div>
        <div>
          <label class="lbl" for="x-cat">Subject (optional)</label>
          <input id="x-cat" v-model="category" class="field" type="text" placeholder="Science" />
        </div>
        <div class="tp-fit">
          <label class="lbl" for="x-rows">Empty rows</label>
          <input id="x-rows" v-model.number="rows" class="field" type="number" min="10" max="500" step="10" style="width: 7rem" />
        </div>
      </div>

      <div v-if="wantsData" class="tp-row">
        <div>
          <label class="lbl" for="x-ds">Name of the data table</label>
          <input id="x-ds" v-model="datasetName" class="field" type="text" placeholder="Plant heights" />
        </div>
        <div>
          <label class="lbl" for="x-cols">Column names, separated by commas</label>
          <input id="x-cols" v-model="columns" class="field" type="text" placeholder="Student, Plant, Week 1 (cm), Week 2 (cm)" />
        </div>
      </div>

      <div><a class="btn green" :href="templateUrl" download>Download the Excel sheet</a></div>
    </div>

    <div class="tp-note">
      When the students have filled the sheet in, add it in <button type="button" class="linkish" @click="$emit('go', 'add')">Add data</button>.
      You can drop pictures, recordings and documents there too.
    </div>
  </div>
</template>

<style scoped>
.kinds { border: 0; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: .7rem; }
.kinds legend { padding: 0; margin-bottom: .5rem; }
.kind { display: flex; gap: .7rem; align-items: flex-start; padding: .7rem .9rem; border: 3px solid var(--ink); border-radius: 18px; cursor: pointer; background: #fff; }
.kind.on { background: var(--pink-wash); box-shadow: 0 4px 0 var(--ink); }
.kind input { width: 1.4rem; height: 1.4rem; margin-top: .2rem; accent-color: var(--pink-deep); flex: none; }
.linkish { all: unset; cursor: pointer; font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
.linkish:focus-visible { outline: 4px solid var(--ink); outline-offset: 3px; }
</style>
