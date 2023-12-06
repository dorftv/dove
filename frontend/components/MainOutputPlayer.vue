<template>
<<<<<<< HEAD
  <div>
    Main Output
    <VideoPlayer :preview_uri="preview_uri" />
  </div>
=======
    <div>
<VideoPlayer :preview_uri="preview_uri" />
    </div>
>>>>>>> 3eeb711 (WIP: Add nuxt.js frontend.)
</template>

<script setup>

const { preview_uri } = defineProps(['preview_uri'])

</script>

<style scoped> 
<<<<<<< HEAD
:deep() media-player {
  aspect-ratio: 16 / 9;
  width: 400px;
  height: 225;
=======
media-player {
  aspect-ratio: 16 / 9;
  width: 480px;
  height: 360px;
>>>>>>> 3eeb711 (WIP: Add nuxt.js frontend.)
}
</style>
