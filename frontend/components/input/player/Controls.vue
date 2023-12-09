<template>
  <div :class="statusClass">
    <UIcon name="i-heroicons-stop-circle" class="h-5 w-5" color="gray" @click="submitStop"/>
    <UIcon name="i-heroicons-pause-circle" class="h-5 w-5" color="gray" @click="submitPause"/>
    <UIcon name="i-heroicons-play-circle" class="h-5 w-5" color="gray" @click="submitPlay"/>
    <nuxt-icon name="admin/badge"></nuxt-icon>    {{ status }}
  </div>        
</template>

<script setup>

import { computed } from "@vue/reactivity"

const props = defineProps({
  status: String,
  uid: String
})
//const status = ref(input.status)

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

const statusClass = computed(() => {
switch (props.status) {
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
