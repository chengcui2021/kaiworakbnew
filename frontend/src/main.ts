import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import './styles/main.css'

// Apply the saved theme variant class before mount to avoid a flash of the
// default theme; useColorMode (light/dark) is initialized by useTheme.ts,
// shared as a singleton with the first component that imports it.
const savedTheme = localStorage.getItem('app-theme') || 'violet'
document.documentElement.classList.add(`theme-${savedTheme}`)

createApp(App).use(createPinia()).use(router).mount('#app')
