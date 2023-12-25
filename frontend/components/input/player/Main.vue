<template>
  <div class="">
      <InputPlayerHeader   :uid="uid" />
      <VideoPlayer   v-if="previewEnabled || inputEnabled" :uid="input.uid" />
      <InputPlayerControls :state="input.state" :uid="input.uid"  :input="input" :inputEnabled="inputEnabled" @enablePreview="(preview) => inputEnabled = preview" />
        <div 
        v-for="mixer in mixers" 
        :key="mixer.uid" 
        class="grid  col-span-2 px-4 py-8">
          <InputPlayerMixer 
            :input="input" 
            :mixer="mixer"/>
      </div>        
  </div>
</template>

<script setup>

import { computed } from "@vue/reactivity"
//<CreateInputUri :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 

const props = defineProps({
  input: Object,
  mixers: Object,
})

const previewEnabled = useCookie('enablePreview')
const inputEnabled = ref(false)
const uid = props.input.uid


</script>

<style>

</style>

