
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  ssr: false,
  nitro: {
    devProxy: {
      '/api': 'http://fakeapi:3000',
      '/ws': 'http://fakeapi:9999',
    },
  },  
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
  modules: ['@nuxt/ui', 'nuxt-icon-tw', '@nuxtjs/tailwindcss'],
  link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
  template: {
    compilerOptions: {
      "types": ["vidstack/vue"],
      isCustomElement: (tag) => tag.startsWith('media-'),
    },
  },
  
})

