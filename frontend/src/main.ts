import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import './style.css'
import { router } from './app/router'

createApp(App).use(createPinia()).use(VueQueryPlugin).use(router).mount('#app')
