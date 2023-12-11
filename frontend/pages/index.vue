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
import { watch, ref, onMounted, onUnmounted } from 'vue';

const webSocket = ref(null);
const { data: inputs } = await useFetch('/api/inputs');
const { data: mixers } = await useFetch('/api/mixers');
const { data: outputs } = await useFetch('/api/outputs');

const entityMap = {
  input: inputs,
  mixer: mixers,
  output: outputs
};

const updateEntity = (type, updatedEntity) => {
  const entities = entityMap[type].value;
  const index = entities.findIndex(entity => entity.uid === updatedEntity.uid);
  if (index !== -1) {
    entities[index] = { ...entities[index], ...updatedEntity };
  }
};

const addEntity = (type, newEntity) => {
  const entities = entityMap[type].value;
  if (!entities.some(entity => entity.uid === newEntity.uid)) {
    entities.push(newEntity);
  }
};

const deleteEntity = (type, entityToDelete) => {
  entityMap[type].value = entityMap[type].value.filter(entity => entity.uid !== entityToDelete.uid);
};

onMounted(() => {
  webSocket.value = new WebSocket('ws://localhost:9999');
  webSocket.value.onmessage = (event) => {
    const message = JSON.parse(event.data);
    const actionMap = {
      CREATE: addEntity,
      UPDATE: updateEntity,
      DELETE: deleteEntity
    };
    const action = actionMap[message.channel];
    if (action && entityMap[message.type]) {
      action(message.type, message.data);
    } else {
      console.warn('Unknown Type or Channel:', message.type, message.channel);
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

const watchEntities = (entities) => {
  watch(entities, (newEntities, oldEntities) => {
    // Handle entity changes
  }, { deep: true });
};

watchEntities(inputs);
watchEntities(mixers);
watchEntities(outputs);

</script>

<style scoped>

</style>