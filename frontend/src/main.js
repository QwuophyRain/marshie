import { createApp } from 'vue'
import '@fontsource-variable/grandstander'
import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
import './style.css'
import App from './App.vue'
import { applyCachedTheme } from './brand'

applyCachedTheme()                 // last visit's school colours, before the first paint

createApp(App).mount('#app')
