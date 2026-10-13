// Which little panels are open on the main screen. Kept apart from the conversation so any component can open one.
import { reactive } from 'vue'

export const ui = reactive({
  menu: false,       // the small menu box
  history: false,    // "what we said" sheet
  zoom: null,        // a picture opened full size
})

export function closePanels() {
  ui.menu = false
  ui.history = false
}
