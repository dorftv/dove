<script setup>
//const usePreviewEnabled = useState('enablePreview', () => true)
// use cookie because SSR is disabled
const usePreviewEnabled = useCookie('enablePreview')
</script>

<template>
  <div>
    Enable Preview
    <UToggle v-model="usePreviewEnabled"/>
  </div>
</template>