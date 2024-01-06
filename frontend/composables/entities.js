import { ref, onMounted, onUnmounted } from 'vue';

export function useEntities() {
  const inputs = ref([]);
  const mixers = ref([]);
  const outputs = ref([]);
  const webSocket = ref(null);
  const error = ref(null);

  const addEntity = (type, entity) => {
    entityMap[type].value.push(entity);
  };

  const updateEntity = (type, updatedEntity) => {
    const index = entityMap[type].value.findIndex((entity) => entity.uid === updatedEntity.uid);
    if (index !== -1) {
      entityMap[type].value[index] = { ...entityMap[type].value[index], ...updatedEntity };
    }
  };

  const deleteEntity = (type, deletedEntity) => {
    const index = entityMap[type].value.findIndex((entity) => entity.uid === deletedEntity.uid);
    if (index !== -1) {
      entityMap[type].value.splice(index, 1);
    }
  };

  const entityMap = {
    input: inputs,
    mixer: mixers,
    output: outputs
  };

  onMounted(async () => {
    try {
      const inputsResponse = await useFetch('/api/inputs');
      if (inputsResponse.error.value) throw inputsResponse.error.value;
      inputs.value = inputsResponse.data.value;

      const mixersResponse = await useFetch('/api/mixers');
      if (mixersResponse.error.value) throw mixersResponse.error.value;
      mixers.value = mixersResponse.data.value;

      const outputsResponse = await useFetch('/api/outputs');
      if (outputsResponse.error.value) throw outputsResponse.error.value;
      outputs.value = outputsResponse.data.value;
    } catch (e) {
      error.value = 'Failed to load entities: ' + e.message;
      console.error(error.value);
    }

    webSocket.value = new WebSocket('ws://192.168.23.129:5000/ws');
    webSocket.value.onmessage = (event) => {
      const message = JSON.parse(event.data);
      const action = {
        CREATE: addEntity,
        UPDATE: updateEntity,
        DELETE: deleteEntity
      }[message.channel];
      
      if (action && entityMap[message.type]) {
        action(message.type, message.data);
      } else {
        console.warn('Unknown Type or Channel:', message.type, message.channel);
      }
    };

    webSocket.value.onerror = (wsError) => {
      error.value = 'WebSocket error: ' + wsError.message;
      console.error(error.value);
    };
  });

  onUnmounted(() => {
    if (webSocket.value) {
      webSocket.value.close();
    }
  });

  const sendWebSocketMessage = (message) => {
    if (webSocket.value && webSocket.value.readyState === WebSocket.OPEN) {
      webSocket.value.send(JSON.stringify(message));
    } else {
      error.value = 'WebSocket is not open. Cannot send message.';
    }
  };

  return {
    inputs,
    mixers,
    outputs,
    sendWebSocketMessage,
    error
  };
}