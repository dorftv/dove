
<template>
    <div>     
    <media-player  autoplay stream-type="live" load="eager" title="Sprite Fight"  :src="`${preview_uri}`">
  <media-provider></media-provider>
</media-player>

    </div>
</template>

<script setup>
import 'vidstack/player';
import 'vidstack/player/layouts';
import 'vidstack/player/ui';
import 'vidstack/player/styles/default/theme.css';
import 'vidstack/player/styles/default/layouts/video.css';
import { BeakerIcon } from "@heroicons/vue/20/solid";

const { preview_uri } = defineProps(['preview_uri'])


</script>
 
<style scoped>  
media-player {
  aspect-ratio: 16 / 9;
  width: 320px;
  height: 180;
}
</style>
