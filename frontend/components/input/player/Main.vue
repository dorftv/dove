<template>
  <div>
      <InputPlayerHeader :uid="uid" />
      <VideoPlayer  v-if="enablePreview" :preview_uri="input.uri" />
      <InputPlayerControls :status="input.status" :uid="input.uid"  />
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
