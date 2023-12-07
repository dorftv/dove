<template>
  <div>
    <div class="grid grid-cols-4 gap-5">
      <div v-for="input in inputs" :key="input.uid">
        <InputPlayer :input="input" />

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

// Fetch initial inputs
const { data: inputs } = await useFetch('/api/input')

// Ref for WebSocket instance
const webSocket = ref(null);

onMounted(() => {
  // Establish WebSocket connection
  webSocket.value = new WebSocket('ws://192.168.23.129:9999');

  // Listen for messages
  webSocket.value.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.action === 'UPDATE') {
      updateInput(message);
    }
  };

  // Handle any errors
  webSocket.value.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
});

onUnmounted(() => {
  // Close the WebSocket connection when the component is unmounted
  if (webSocket.value) {
    webSocket.value.close();
  }
});

// Update input function
const updateInput = (updatedInput) => {
  const index = inputs.value.findIndex(input => input.uid === updatedInput.uid);
  if (index !== -1) {
    inputs.value[index] = updatedInput;
  }
};
</script>

<style>
/* Your styles here */
</style>
