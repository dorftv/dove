<template>
  <div class="">
      <MixerPlayerHeader   :mixer="mixer" />
      <VideoPlayer   v-if="previewEnabled || mixerEnabled" :uid="mixer.uid" />
      <div 
        v-for="source in mixer.sources" 
        :key="source.src" 
        class="grid  col-span-2 px-4 py-8">
{{  source }}
      </div>        
      <!--<InputPlayerControls :state="mixer.state" :uid="mixer.uid"  :mixerEnabled="mixerEnabled" @enablePreview="(preview) => mixerEnabled = preview" />-->
  </div>
</template>

<script setup>

import { computed } from "@vue/reactivity"
//<CreateInputUri :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 

const props = defineProps({
  mixer: Object,
})
console.log(props.mixer)
const previewEnabled = useCookie('enablePreview')
const mixerEnabled = ref(false)
const uid = props.mixer.uid


</script>

<style>

</style>

