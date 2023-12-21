<template>
  <div :class="stateClass">
    <Icon name="uil:stop-circle" color="black" size="24px" @click="submitStop"/>
    <Icon name="uil:pause-circle" color="black" size="24px"  @click="submitPause" />
    <Icon name="uil:play-circle" color="black" size="24px" @click="submitPlay"/>
     {{ state }}
     <!-- toggle preview -->
    <Icon name="uil:video-slash" color="black" size="24px"  v-if="!previewEnabled && inputEnabled" @click="$emit('enablePreview', false)"/>
    <Icon name="uil:video" color="black" size="24px"  v-if="!previewEnabled && !inputEnabled"  @click="$emit('enablePreview', true)"/>    
  </div>
</template>

<script setup>

import { computed } from "@vue/reactivity"

const props = defineProps({
  state: String,
  uid: String,
  inputEnabled: Boolean

})
//const state = ref(input.state)

const previewEnabled = useCookie('enablePreview')
  
  function enablePreview() {
    inputEnabled = !prop.inputEnabled
  }
  
const submitPlay = async () => {
    const { data: responseData } = await useFetch('/api/input/delete', {
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

.paused {
background-color: red;
}
</style>
