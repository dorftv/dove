<template>
    {{ source.name }}
    <URange :modelValue="alpha" @update:modelValue="handleChange('alpha', $event)" name="range" :min="0" :max="100" />
    Alpha: {{ alpha }}    
    <URange :modelValue="width" @update:modelValue="handleChange('width', $event)" name="range" :min="0" :max="mixer.width" />
    Width: {{ width }}
    <URange :modelValue="height" @update:modelValue="handleChange('height', $event)" name="range" :min="0" :max="mixer.height" />
    Height: {{ height }}        
    <URange :modelValue="xpos" @update:modelValue="handleChange('xpos', $event)" name="range" :min="0" :max="mixer.width" />
    XPos: {{ xpos }}  
    <URange :modelValue="ypos" @update:modelValue="handleChange('ypos', $event)" name="range" :min="0" :max="mixer.height" />
    YPos: {{ ypos }}
</template>

<script setup>
const props = defineProps({
  source: Object,
  mixer: Object
})

import { useEntities } from '@/composables/entities'; // Adjust the import path as necessary
const { sendWebSocketMessage } = useEntities();

// Update the ref whenever the prop changes
watch(() => props.source.alpha, (newValue) => {
  alpha.value = props.source.alpha * 100;
});  

watch(() => props.source.width, (newValue) => {
  width.value = props.source.width;
});  

watch(() => props.source.height, (newValue) => {
  height.value = props.source.height;
});  

const alpha = ref(props.source.alpha * 100)
const width = ref(props.source.width)
const height = ref(props.source.height)
const xpos = ref(props.source.xpos)
const ypos = ref(props.source.ypos)



const handleChange = (prop, newValue) => {
  if (prop === 'alpha') {
    alpha.value = newValue;
    newValue = newValue / 100;
  } else if (prop === 'width') {
    width.value = newValue;
  } else if (prop === 'height') {
    height.value = newValue;
  } else if (prop === 'xpos') {
    xpos.value = newValue;
  } else if (prop === 'ypos') {
    ypos.value = newValue;
  }

  sendWebSocketMessage({
    type: 'mixer',
    action: 'UPDATE',
    data: {
      uid: props.mixer.uid,
      src: props.source.src,
      [prop]: newValue
    }
  });
};
</script>

<style>
</style>