
<template>
  <div>     

    <media-player ref="mediaPlayer" :muted="muted" viewType="video" autoplay stream-type="live" load="eager" title="Sprite Fight"  :src="`/preview/hls/${uid}/index.m3u8`" class="aspect-video">
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
import HLS from 'hls.js';

import { MediaPlayerElement } from 'vidstack/elements';

const mediaPlayer = ref(null);

onMounted(() => {
  const player = mediaPlayer.value;

  player.addEventListener('provider-change', (event) => {
  const provider = event.detail;
  if (provider?.type === 'hls') {
    provider.library = HLS;
  }
});

player.addEventListener('can-play', () => {
  player.play()
  console.log(player.state)
});

  player.addEventListener('hls-error', (event) => {
    const provider = event.detail;
    const src = player.src
    // TODO find a way to handle error
 });
});

const props = defineProps({
  uid: String,
  muted: String
})

</script>
 
<style scoped>  

</style>
