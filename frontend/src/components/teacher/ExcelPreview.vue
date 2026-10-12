<script setup>
import { computed } from 'vue'

const props = defineProps({ preview: { type: Object, required: true } })
const nothingToAdd = computed(() => !props.preview.to_add && !props.preview.datasets.length)
</script>

<template>
  <div class="xp">
    <ul class="tp-list">
      <li v-for="s in preview.sheets" :key="s.name" class="tp-item">
        <span class="main"><span class="tp-tag">{{ s.type }}</span><b>{{ s.name }}</b>: {{ s.rows }} {{ s.rows === 1 ? 'row' : 'rows' }} ready</span>
      </li>
    </ul>

    <div v-if="preview.sample.length">
      <p class="lbl">A few of the things Marshie would learn</p>
      <div class="tp-scroll">
        <table class="tp-table">
          <thead><tr><th>Question or topic</th><th>Answer</th></tr></thead>
          <tbody><tr v-for="(s, i) in preview.sample" :key="i"><td>{{ s.question }}</td><td>{{ s.answer }}</td></tr></tbody>
        </table>
      </div>
    </div>

    <div v-for="d in preview.datasets" :key="d.name">
      <p class="lbl">Data table “{{ d.name }}” ({{ d.rows }} rows)</p>
      <div class="tp-scroll">
        <table class="tp-table">
          <thead><tr><th v-for="c in d.columns" :key="c">{{ c }}</th></tr></thead>
          <tbody><tr v-for="(r, i) in d.preview" :key="i"><td v-for="(c, j) in d.columns" :key="j">{{ Array.isArray(r) ? r[j] : r[c] }}</td></tr></tbody>
        </table>
      </div>
    </div>

    <p v-if="preview.skipped_examples" class="hint">Skipped {{ preview.skipped_examples }} grey example {{ preview.skipped_examples === 1 ? 'row' : 'rows' }}.</p>

    <div v-if="preview.error_count" class="tp-note bad">
      <b>{{ preview.error_count }} {{ preview.error_count === 1 ? 'row needs' : 'rows need' }} fixing</b> and will be left out:
      <ul>
        <li v-for="(e, i) in preview.errors.slice(0, 12)" :key="i">
          <template v-if="e.sheet">Sheet “{{ e.sheet }}”<template v-if="e.row">, row {{ e.row }}</template>: </template>{{ e.message }}
        </li>
      </ul>
      <p v-if="preview.error_count > 12" class="hint">…and {{ preview.error_count - 12 }} more.</p>
    </div>
    <div v-if="preview.warnings.length" class="tp-note">
      <ul><li v-for="(w, i) in preview.warnings.slice(0, 5)" :key="i">{{ w.sheet }} row {{ w.row }}: {{ w.message }}</li></ul>
    </div>

    <p v-if="nothingToAdd" class="tp-note bad">I could not find anything to learn in this file. Check that it is one of the sheets made here, with the Question and Answer columns filled in.</p>
  </div>
</template>

<style scoped>
.xp { display: flex; flex-direction: column; gap: .9rem; }
.xp ul { margin: .4rem 0 0 1.1rem; padding: 0; }
.xp .tp-list { margin: 0; }
</style>
