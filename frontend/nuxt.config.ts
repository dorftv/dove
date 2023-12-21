
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  ssr: false,
  static: true,
  nitro: {
    devProxy: {
      '/api': 'http://192.168.23.129:5000/api',
      '/preview': 'http://192.168.23.129:5000/preview',
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
  modules: ['@nuxt/ui', 'nuxt-icon'],
  link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
  template: {
    compilerOptions: {
      "types": ["vidstack/vue"],
      isCustomElement: (tag) => tag.startsWith('media-'),
    },
  },
  
})

