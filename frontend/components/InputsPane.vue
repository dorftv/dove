<template>
  <div class="grid grid-cols-4 gap-5">
    <div v-for="input in inputs" :key="input.uid">
      <InputPlayer :input="input" />
    </div>
  </div>
</template>

<script setup>
import { watch,  ref, onMounted, onUnmounted } from 'vue';

const webSocket = ref(null);
const { data: inputs } = await useFetch('/api/input')

onMounted(() => {
  webSocket.value = new WebSocket('ws://localhost:9999');

  webSocket.value.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'input') {
      handleInputMessage(message.channel, message.data);
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

const handleInputMessage = (channel, data) => {
  switch (channel) {
    case 'CREATE':
      addInput(data);
      break;
    case 'UPDATE':
      updateInput(data);
      break;
    case 'DELETE':
      deleteInput(data);
      break;
    default:
      console.warn('Unhandled channel:', channel);
  }
};

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

</script>

<style>
</style>
