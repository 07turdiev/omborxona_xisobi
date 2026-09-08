import './assets/main.css'
// Boshliq bergan StoreFlow dizayni. Tailwind'dan keyin import qilinadi,
// shunda uning qoidalari ustun bo'ladi.
import './assets/app.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
