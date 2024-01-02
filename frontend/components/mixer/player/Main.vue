<template>
  <div class="">
      <MixerPlayerHeader   :mixer="mixer" />
      <VideoPlayer   v-if="previewEnabled || mixerEnabled" :uid="mixer.uid" />
      <UTable :rows="mergedSources" :columns="columns" :empty-state="{}" >
        <template #empty-state>
      <div class="flex flex-col items-center justify-center py-6 gap-3">
        no input in mix!
      </div>
    </template>

    </UTable>
      <!--<InputPlayerControls :state="mixer.state" :uid="mixer.uid"  :mixerEnabled="mixerEnabled" @enablePreview="(preview) => mixerEnabled = preview" />-->
  </div>
</template> 

<script setup>

import { computed } from "@vue/reactivity"
//<CreateInputUri :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 
const columns = [{
  key: 'name',
  label: 'Input'
}, {
  key: 'width',
  label: 'width'
}, {
  key: 'height',
  label: 'height'
}, {
  key: 'xpos',
  label: 'x'
}, {
  key: 'ypos',
  label: 'y'
}, {
  key: 'zorder',
  label: 'z'
}, {
  key: 'alpha',
  label: 'alpha'
}]

const props = defineProps({
  mixer: Object,
  inputs: Object
})

// Computed property to flatten and merge mixerSources with inputs
const mergedSources = computed(() => {
  return props.mixer.sources.map(source => {
    // Find the matching input by comparing source.src with input.uid
    const matchingInput = props.inputs.find(input => input.uid === source.src);

    // Merge source with matchingInput; if no match is found, return source as is
    return matchingInput ? { ...source, ...matchingInput } : source;
  });
});


console.log(props.mixer)
const previewEnabled = useCookie('enablePreview')
const mixerEnabled = ref(false)
const uid = props.mixer.uid


</script>

<style>

</style>

