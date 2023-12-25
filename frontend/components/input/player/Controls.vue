<template>
  <div :class="stateClass">
    <Icon name="uil:stop-circle" color="black" size="24px" @click="submitStop"/>
    <Icon name="uil:pause-circle" color="black" size="24px"  @click="submitPause" />
    <Icon name="uil:play-circle" color="black" size="24px" @click="submitPlay"/>
     {{ state }}
     <!-- toggle preview -->
    <Icon name="uil:video-slash" color="black" size="24px"  v-if="!previewEnabled && inputEnabled" @click="$emit('enablePreview', false)"/>
    <Icon name="uil:video" color="black" size="24px"  v-if="!previewEnabled && !inputEnabled"  @click="$emit('enablePreview', true)"/>    
    <div>
    <URange v-model="volume" name="range" :min="0" :max="100" />
      Volume: {{  volume  }}          
    </div>    
  </div>
</template>

<script setup>
import { inject } from 'vue';
import { computed } from "@vue/reactivity"
const props = defineProps({
  input: Object,
  state: String,
  uid: String,
  inputEnabled: Boolean

})
const webSocket = inject('webSocket');
const volume = ref(props.input.volume * 100)
    // Watch for changes in the reactive variable
const data = {
  type: 'message',
  content: 'Hello, World!',
  timestamp: Date.now()
};
    watch(props.volume, (newValue, oldValue) => {
      // Send a message when the variable changes
      if (webSocket && webSocket.readyState === WebSocket.OPEN) {
        console.log(newValue)
        webSocket.send(JSON.stringify(data));
      }
    });

    
//const state = ref(input.state)

const previewEnabled = useCookie('enablePreview')
  
  function enablePreview() {
    inputEnabled = !prop.inputEnabled
  }
  
const submitPlay = async () => {
    const { data: responseData } = await useFetch('/api/inputs/delete', {
        method: 'post',
        body: { 
          uid: props.uid,
        }
    })
}

const submitPause = async () => {
    const { data: responseData } = await useFetch('/api/input/delete', {
        method: 'post',
        body: { 
          uid: props.uid,
        }
    })
}
const submitStop = async () => {
    const { data: responseData } = await useFetch('/api/input/delete', {
        method: 'post',
        body: { 
          uid: props.uid,
        }
    })
}

const stateClass = computed(() => {
switch (props.state) {
  case 'PLAYING':
    console.log("play")
    return 'playing';
  case 'BUFFERING':
    console.log("buffer")
    return 'buffering';
  case 'PENDING':
    console.log("pending")
    return 'pending';
  case 'PAUSED':
    console.log("paused")
    return 'paused';
    case 'EOS':
    console.log("eos")
    return 'eos';    
  default:
    console.log("Status unknown")
    return '';
}
});



</script>

<style scoped>


.playing {
background-color: green;

}

.buffering {
background-color: orange;
}

.pending {
background-color: gray;
}

.paused, .eos {
background-color: red;
}
</style>
