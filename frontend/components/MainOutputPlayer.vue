<template>
  <div>
    Main Output
    <VideoPlayer :preview_uri="preview_uri" />
  </div>
</template>

<script setup>

const { preview_uri } = defineProps(['preview_uri'])

</script>

<style scoped> 
:deep() media-player {
  aspect-ratio: 16 / 9;
  width: 400px;
  height: 225;
}
</style>
