import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import './style.css'

createApp(App).use(createPinia()).use(VueQueryPlugin).mount('#app')
