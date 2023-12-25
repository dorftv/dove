<template>
    <div class="websocket-panel">
      <h2>WebSocket Messages</h2>
      <ul>
        <li v-for="(message, index) in messages" :key="index">{{ message }}</li>
      </ul>
    </div>
  </template>
  
  <script>
  export default {
    data() {
      return {
        socket: null,
        messages: []
      };
    },
    mounted() {
      this.setupWebSocket();
    },
    methods: {
      setupWebSocket() {
        this.socket = new WebSocket('ws://localhost:5000/ws');
  
        this.socket.onmessage = (event) => {
          this.messages.push(event.data);
        };
  
        this.socket.onerror = (error) => {
          console.error('WebSocket Error:', error);
        };
      }
    },
    beforeDestroy() {
      if (this.socket) {
        this.socket.close();
      }
    }
  };
  </script>
  
  <style scoped>
  .websocket-panel {
    border: 1px solid #ccc;
    padding: 20px;
    margin-top: 20px;
  }
  .websocket-panel h2 {
    margin-bottom: 10px;
  }
  .websocket-panel ul {
    list-style-type: none;
    padding: 0;
  }
  .websocket-panel li {
    margin-bottom: 5px;
  }
  </style>
  