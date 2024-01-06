// useEntities.js
import { ref } from 'vue';
import { useWebSocket } from './useWebSocket';

export function useEntities() {
  const inputs = ref([]);
  const mixers = ref([]);
  const outputs = ref([]);
  const { sendWebSocketMessage, error } = useWebSocket();

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

  // Fetch entities from API
  const fetchEntities = async () => {
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
  };

  // You may need to call this method to fetch entities when the component using this composable is mounted
  // fetchEntities();

  // Handle WebSocket messages
  const handleWebSocketMessage = (message) => {
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

  return {
    inputs,
    mixers,
    outputs,
    sendWebSocketMessage,
    handleWebSocketMessage,
    error,
    fetchEntities  // Expose the fetchEntities method if you need to call it from outside
  };
}