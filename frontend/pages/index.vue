<template>
  <div > 
    
    <MainOutputPlayer preview_uri="http://localhost:88/preview/playlist.m3u8" />

    <div class="grid grid-cols-4 gap-5">
      <div v-for="input in inputs" :key="input.uid">
        <InputPlayerMain :input="input" />
      </div>
    </div>
  
  </div>
</template>

<script setup>

import { watch,  ref, onMounted, onUnmounted } from 'vue';

const webSocket = ref(null);
const { data: inputs } = await useFetch('/api/inputs')
const { data: mixers } = await useFetch('/api/mixers')
const { data: outputs } = await useFetch('/api/inputs')



onMounted(() => {
  webSocket.value = new WebSocket('ws://localhost:9999');

  webSocket.value.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'input') {
      handleInputMessage(message.type, message.channel, message.data);
    }
  };

  webSocket.value.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
});

onUnmounted(() => {
  if (webSocket.value) {
    webSocket.value.close();
  }
});

const handleInputMessage = (type, channel, data) => {
  switch (channel) {
    case 'CREATE':
      if      (type === 'input') addInput(data)
      else if (type === 'mixer') addMixer(data)
      else if (type === 'output') addOutput(data)
      else console.warn('Unknown Type:',type);
      break;
    case 'UPDATE':
      if      (type === 'input') updateInput(data)
      else if (type === 'mixer') updateMixer(data)
      else if (type === 'output') updateOutput(data)
      else console.warn('Unknown Type:',type);
      break;
      break;
    case 'DELETE':
      if      (type === 'input') deleteInput(data)
      else if (type === 'mixer') deleteMixer(data)
      else if (type === 'output') deleteOutput(data)
      else console.warn('Unknown Type:',type);
      break;
      break;
    default:
      console.warn('Unhandled channel:', channel);
  }
};

// Handle Inputs Updates
const updateInput = (updatedInput) => {
  const index = inputs.value.findIndex(input => input.uid === updatedInput.uid);
  if (index !== -1) {
    inputs.value[index] = { ...inputs.value[index], ...updatedInput };
  }
};

const addInput = (newInput) => {
  const exists = inputs.value.some(input => input.uid === newInput.uid);
  if (!exists) {
    inputs.value.push(newInput);
  }
};

const deleteInput = (inputToDelete) => {
  inputs.value = inputs.value.filter(input => input.uid !== inputToDelete.uid);
};

watch(inputs, (newInput, oldInput) => {

}, { deep: true });

// Handle mixers Updates
const updateMixer = (updatedMixer) => {
  const index = mixers.value.findIndex(mixer => mixer.uid === updatedMixer.uid);
  if (index !== -1) {
    mixers.value[index] = { ...mixers.value[index], ...updatedMixer };
  }
};

const addMixer = (newMixer) => {
  const exists = mixers.value.some(mixer => mixer.uid === newMixer.uid);
  if (!exists) {
    mixers.value.push(newMixer);
  }
};

const deleteMixer = (mixerToDelete) => {
  mixers.value = mixers.value.filter(mixer => mixer.uid !== mixerToDelete.uid);
};

watch(mixers, (newMixer, oldmixer) => {

}, { deep: true });

// Handle outputs Updates
const updateOutput = (updatedOutput) => {
  const index = outputs.value.findIndex(output => output.uid === updatedOutput.uid);
  if (index !== -1) {
    outputs.value[index] = { ...outputs.value[index], ...updatedOutput };
  }
};

const addOutput = (newOutput) => {
  const exists = outputs.value.some(output => output.uid === newOutput.uid);
  if (!exists) {
    outputs.value.push(newOutput);
  }
};

const deleteOutput = (outputToDelete) => {
  outputs.value = outputs.value.filter(output => output.uid !== outputToDelete.uid);
};

watch(outputs, (newOutput, oldOutput) => {

}, { deep: true });

</script>
<style scoped>  

</style>
