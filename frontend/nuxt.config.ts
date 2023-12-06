
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
<<<<<<< HEAD
  ssr: false,
  nitro: {
    devProxy: {
      '/api': 'http://fakeapi:3000',
      '/ws': 'http://fakeapi:9999',
    },
  },  
=======

>>>>>>> 3eeb711 (WIP: Add nuxt.js frontend.)
  devtools: { enabled: true },
  css: ["@/assets/css/tailwind.css"],
  postcss: {
    plugins: {
      "postcss-import": {},
      "tailwindcss/nesting": {},
      tailwindcss: {},  
      autoprefixer: {},
    },
  },
  modulesDir: ['./node_modules'],
<<<<<<< HEAD
  modules: ['@nuxt/ui'],
=======
  modules: ['@nuxtjs/tailwindcss'],
>>>>>>> 3eeb711 (WIP: Add nuxt.js frontend.)
  link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
  template: {
    compilerOptions: {
      "types": ["vidstack/vue"],
      isCustomElement: (tag) => tag.startsWith('media-'),
    },
  },
<<<<<<< HEAD
  
=======
>>>>>>> 3eeb711 (WIP: Add nuxt.js frontend.)
})

