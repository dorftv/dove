<template>
  <div class="">
      <MixerPlayerHeader   :uid="uid" />
      <VideoPlayer   v-if="previewEnabled || mixerEnabled" :uid="mixer.uid" />
      <!--<InputPlayerControls :state="mixer.state" :uid="mixer.uid"  :mixerEnabled="mixerEnabled" @enablePreview="(preview) => mixerEnabled = preview" />-->
  </div>
</template>

<script setup>

import { computed } from "@vue/reactivity"
//<CreateInputUri :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 

const props = defineProps({
  mixer: Object,
})

const previewEnabled = useCookie('enablePreview')
const mixerEnabled = ref(false)
const uid = props.mixer.uid


</script>

<style>

</style>

