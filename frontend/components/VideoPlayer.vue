
<template>
  <div>     

    <media-player  viewType="video" autoplay stream-type="live" load="eager" title="Sprite Fight"  :src="`/preview/hls/${uid}/index.m3u8`" class="aspect-video">
      <media-provider></media-provider>
      <media-video-layout></media-video-layout>

    </media-player>

  </div>
</template>

<script setup>
import 'vidstack/player';
import 'vidstack/player/layouts';
import 'vidstack/player/ui';
import 'vidstack/player/styles/default/theme.css';
import 'vidstack/player/styles/default/layouts/video.css';





const { uid } = defineProps(['uid'])

</script>
 
<style scoped>  

</style>
