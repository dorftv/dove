<template>
  <div>
    Main Output
    <VideoPlayer :preview_uri="preview_uri" />
  </div>
</template>

<script setup>


const props = defineProps({
  preview_uri: String,
})

</script>

<style scoped> 

</style>
