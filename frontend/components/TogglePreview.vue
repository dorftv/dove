<script setup>
const enablePreview = ref(true)
//const color = useColor() // Same as useState('color')
const usePreviewEnabled =  useState('enablePreview')
// TODO make available global

</script>

<template>
  <div>
    Enable Preview
    <UToggle v-model="usePreviewEnabled"/>
  </div>
</template>