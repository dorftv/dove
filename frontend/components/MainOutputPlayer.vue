<template>
    <div>
<VideoPlayer :preview_uri="preview_uri" />
    </div>
</template>

<script setup>

const { preview_uri } = defineProps(['preview_uri'])

</script>

<style scoped> 
media-player {
  aspect-ratio: 16 / 9;
  width: 480px;
  height: 360px;
}
</style>
