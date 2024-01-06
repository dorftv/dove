// useWebSocket.js
import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocket(url) {
  const webSocket = ref(null);
  const error = ref(null);

  onMounted(() => {
    webSocket.value = new WebSocket(url);

    webSocket.value.onmessage = (event) => {
      // Handle incoming WebSocket messages
      console.log('WebSocket message received:', event.data);
    };

    webSocket.value.onerror = (wsError) => {
      error.value = `WebSocket error: ${wsError.message}`;
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
    webSocket,
    sendWebSocketMessage,
    error
  };
}