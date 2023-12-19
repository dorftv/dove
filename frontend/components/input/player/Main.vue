<template>
  <div class="">
      <InputPlayerHeader   :uid="uid" />
      <VideoPlayer   v-if="previewEnabled || inputEnabled" :preview_uri="input.uri" />
      <InputPlayerControls :status="input.status" :uid="input.uid"  :inputEnabled="inputEnabled" @enablePreview="(preview) => inputEnabled = preview" />
  </div>
</template>

<script setup>

import { computed } from "@vue/reactivity"
//<CreateInputUri :isOpen="isOpen" @close="(closing) => isOpen = closing" /> 

const props = defineProps({
  input: Object,
})

const previewEnabled = useCookie('enablePreview')
const inputEnabled = ref(false)
const uid = props.input.uid


</script>

<style>

</style>

