<template>
  <div>
    <div>

      <div :class="statusClass">
        <div>
          Input: {{ uid }}
        </div>
        <div>
          Status: {{ status }}
        </div>
        </div>        
      </div>
    </div>
</template>

<script setup>

import { computed } from "@vue/reactivity"

const props = defineProps({
  status: String,
  status: String
})
//const status = ref(input.status)


const statusClass = computed(() => {
switch (props.status) {
  case 'PLAYING':
    console.log("play")
    return 'playing';
  case 'BUFFERING':
    console.log("buffer")
    return 'buffering';
  case 'PENDING':
    console.log("pend")
    return 'pending';
    case 'PAUSED':
    console.log("paused")
    return 'paused';
  default:
    console.log("no check")
    return '';
}
});



</script>

<style>
div {
margin: 1em;
}

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
