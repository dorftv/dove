<template>
  <div>
    <div>
      <InputPlayerControls :uid="uid" />
<div v-if="enablePreview">
      <VideoPlayer :preview_uri="input.uri" />
       <InputPlayerStatus :status="input.status" :uid="input.uid" />

      <div :class="statusClass">
        <div>
          Input: {{ input.uid }}
        </div>
        <div>
          Status: {{ input.status }}
        </div>
        </div>        
      </div>
    </div>
  </div>
</template>

<script setup>

import { computed } from "@vue/reactivity"

const props = defineProps({
  input: Object
})

const enablePreview = useCookie('enablePreview')
const uid = props.input.uid

</script>

<style>

</style>
