
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({

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
  modules: ['@nuxtjs/tailwindcss'],
  link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
  template: {
    compilerOptions: {
      "types": ["vidstack/vue"],
      isCustomElement: (tag) => tag.startsWith('media-'),
    },
  },
})

